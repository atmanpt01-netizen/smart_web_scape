import uuid
from datetime import datetime, timedelta

import structlog
from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.schemas import AlertResponse
from backend.db.models import Alert, Schedule, Url, VisitLog
from backend.db.session import get_db

router = APIRouter()
logger = structlog.get_logger(__name__)


@router.get("/summary")
async def get_summary(session: AsyncSession = Depends(get_db)) -> dict:
    """대시보드 KPI 요약을 반환합니다."""
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

    # 총 URL 수
    total_urls = (await session.execute(select(func.count()).select_from(Url))).scalar_one()
    # 활성 URL 수
    active_urls = (
        await session.execute(select(func.count()).select_from(Url).where(Url.is_active.is_(True)))
    ).scalar_one()

    # 전체 성공률 (최근 7일)
    seven_days_ago = datetime.utcnow() - timedelta(days=7)
    total_logs = (
        await session.execute(
            select(func.count()).select_from(VisitLog).where(VisitLog.visited_at >= seven_days_ago)
        )
    ).scalar_one()
    success_logs = (
        await session.execute(
            select(func.count())
            .select_from(VisitLog)
            .where(VisitLog.visited_at >= seven_days_ago, VisitLog.success.is_(True))
        )
    ).scalar_one()
    success_rate = (success_logs / total_logs) if total_logs > 0 else 0.0

    # 오늘 수집 건수
    today_items = (
        await session.execute(
            select(func.coalesce(func.sum(VisitLog.items_extracted), 0))
            .where(VisitLog.visited_at >= today_start, VisitLog.success.is_(True))
        )
    ).scalar_one()

    return {
        "total_urls": total_urls,
        "active_urls": active_urls,
        "success_rate": round(success_rate, 4),
        "today_items": today_items,
        "period_days": 7,
    }


@router.get("/success-rate")
async def get_success_rate_trend(
    days: int = Query(default=30, ge=1, le=90),
    session: AsyncSession = Depends(get_db),
) -> list[dict]:
    """일별 성공률 추이를 반환합니다."""
    start_date = datetime.utcnow() - timedelta(days=days)

    result = await session.execute(
        select(
            func.date_trunc("day", VisitLog.visited_at).label("date"),
            func.count().label("total"),
            func.sum(func.cast(VisitLog.success, type_=func.count().type)).label("success_count"),
        )
        .where(VisitLog.visited_at >= start_date)
        .group_by(func.date_trunc("day", VisitLog.visited_at))
        .order_by(func.date_trunc("day", VisitLog.visited_at))
    )

    rows = result.all()
    return [
        {
            "date": str(row.date)[:10] if row.date else None,
            "total": row.total,
            "success_count": row.success_count or 0,
            "success_rate": round((row.success_count or 0) / row.total, 4) if row.total > 0 else 0.0,
        }
        for row in rows
    ]


@router.get("/pipeline-stats")
async def get_pipeline_stats(
    days: int = Query(default=7, ge=1, le=30),
    session: AsyncSession = Depends(get_db),
) -> list[dict]:
    """파이프라인별 사용 분포를 반환합니다."""
    start_date = datetime.utcnow() - timedelta(days=days)

    result = await session.execute(
        select(VisitLog.pipeline_name, func.count().label("count"))
        .where(VisitLog.visited_at >= start_date)
        .group_by(VisitLog.pipeline_name)
        .order_by(func.count().desc())
    )

    return [{"pipeline": row.pipeline_name, "count": row.count} for row in result.all()]


@router.get("/category-stats")
async def get_category_stats(session: AsyncSession = Depends(get_db)) -> list[dict]:
    """카테고리별 성공률을 반환합니다."""
    result = await session.execute(
        select(
            Url.category,
            func.count(VisitLog.id).label("total"),
            func.sum(func.cast(VisitLog.success, type_=func.count().type)).label("success_count"),
        )
        .join(Url, VisitLog.url_id == Url.id)
        .group_by(Url.category)
        .order_by(func.count(VisitLog.id).desc())
    )

    return [
        {
            "category": row.category,
            "total": row.total,
            "success_count": row.success_count or 0,
            "success_rate": round((row.success_count or 0) / row.total, 4) if row.total > 0 else 0.0,
        }
        for row in result.all()
    ]


@router.get("/recent-visits")
async def get_recent_visits(
    limit: int = Query(default=20, ge=1, le=100),
    session: AsyncSession = Depends(get_db),
) -> list[dict]:
    """최근 방문 목록을 반환합니다."""
    result = await session.execute(
        select(VisitLog).order_by(VisitLog.visited_at.desc()).limit(limit)
    )
    logs = result.scalars().all()

    return [
        {
            "id": str(log.id),
            "url": log.url,
            "success": log.success,
            "pipeline_name": log.pipeline_name,
            "duration_ms": log.duration_ms,
            "visited_at": log.visited_at.isoformat() if log.visited_at else None,
        }
        for log in logs
    ]


@router.get("/alerts")
async def get_alerts(
    is_read: bool | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    session: AsyncSession = Depends(get_db),
) -> list[AlertResponse]:
    """알림 목록을 반환합니다."""
    query = select(Alert).order_by(Alert.created_at.desc()).limit(limit)
    if is_read is not None:
        query = query.where(Alert.is_read == is_read)

    result = await session.execute(query)
    alerts = result.scalars().all()
    return [AlertResponse.model_validate(a) for a in alerts]


@router.put("/alerts/{alert_id}/read")
async def mark_alert_read(alert_id: uuid.UUID, session: AsyncSession = Depends(get_db)) -> dict:
    """알림을 읽음으로 표시합니다."""
    result = await session.execute(select(Alert).where(Alert.id == alert_id))
    alert = result.scalar_one_or_none()
    if not alert:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="알림을 찾을 수 없습니다.")

    alert.is_read = True
    await session.commit()
    return {"id": str(alert_id), "is_read": True}


@router.post("/alerts/read-all")
async def mark_all_alerts_read(session: AsyncSession = Depends(get_db)) -> dict:
    """모든 알림을 읽음으로 표시합니다."""
    from sqlalchemy import update
    await session.execute(update(Alert).where(Alert.is_read.is_(False)).values(is_read=True))
    await session.commit()
    return {"message": "모든 알림을 읽음으로 처리했습니다."}


@router.get("/schedules/upcoming")
async def get_upcoming_schedules(
    limit: int = Query(default=5, ge=1, le=20),
    session: AsyncSession = Depends(get_db),
) -> list[dict]:
    """다음 실행 예정 스케줄을 반환합니다."""
    now = datetime.utcnow()
    result = await session.execute(
        select(Schedule)
        .where(Schedule.is_active.is_(True), Schedule.next_run_at >= now)
        .order_by(Schedule.next_run_at)
        .limit(limit)
    )
    schedules = result.scalars().all()

    return [
        {
            "id": str(s.id),
            "url_id": str(s.url_id),
            "cron_expression": s.cron_expression,
            "next_run_at": s.next_run_at.isoformat() if s.next_run_at else None,
            "run_count": s.run_count,
        }
        for s in schedules
    ]
