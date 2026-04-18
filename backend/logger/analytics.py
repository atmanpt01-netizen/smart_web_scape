"""방문 이력 기반 통계 분석 엔진."""
from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models import Url, VisitLog


class VisitAnalytics:
    """대시보드 통계 데이터 생성."""

    async def get_success_rate_trend(
        self, session: AsyncSession, days: int = 30
    ) -> list[dict]:
        """일별 성공률 추이를 반환합니다."""
        start_date = datetime.utcnow() - timedelta(days=days)

        result = await session.execute(
            select(
                func.date_trunc("day", VisitLog.visited_at).label("date"),
                func.count().label("total"),
                func.count(VisitLog.id).filter(VisitLog.success.is_(True)).label("success_count"),
            )
            .where(VisitLog.visited_at >= start_date)
            .group_by(func.date_trunc("day", VisitLog.visited_at))
            .order_by(func.date_trunc("day", VisitLog.visited_at))
        )

        return [
            {
                "date": str(row.date)[:10] if row.date else None,
                "total": row.total,
                "success_count": row.success_count or 0,
                "success_rate": round((row.success_count or 0) / row.total, 4) if row.total > 0 else 0.0,
            }
            for row in result.all()
        ]

    async def get_pipeline_distribution(self, session: AsyncSession, days: int = 7) -> dict:
        """파이프라인별 사용 분포를 반환합니다."""
        start_date = datetime.utcnow() - timedelta(days=days)

        result = await session.execute(
            select(VisitLog.pipeline_name, func.count().label("count"))
            .where(VisitLog.visited_at >= start_date)
            .group_by(VisitLog.pipeline_name)
        )

        rows = result.all()
        total = sum(r.count for r in rows)
        return {
            row.pipeline_name: {
                "count": row.count,
                "percentage": round(row.count / total * 100, 1) if total > 0 else 0.0,
            }
            for row in rows
        }

    async def get_category_success_rates(self, session: AsyncSession) -> list[dict]:
        """카테고리별 성공률을 반환합니다."""
        result = await session.execute(
            select(
                Url.category,
                func.count(VisitLog.id).label("total"),
                func.count(VisitLog.id).filter(VisitLog.success.is_(True)).label("success_count"),
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
