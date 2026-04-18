import uuid

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.schemas import ScheduleCreate, ScheduleResponse, ScheduleUpdate
from backend.db.models import Schedule, Url
from backend.db.session import get_db

router = APIRouter()
logger = structlog.get_logger(__name__)


@router.post("", response_model=ScheduleResponse, status_code=status.HTTP_201_CREATED)
async def create_schedule(
    payload: ScheduleCreate,
    session: AsyncSession = Depends(get_db),
) -> Schedule:
    """스케줄을 등록합니다."""
    # URL 존재 확인
    url_result = await session.execute(select(Url).where(Url.id == payload.url_id))
    if not url_result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="URL을 찾을 수 없습니다.")

    schedule = Schedule(
        url_id=payload.url_id,
        schedule_type=payload.schedule_type,
        cron_expression=payload.cron_expression,
        timezone=payload.timezone,
        max_retries=payload.max_retries,
        retry_delay_minutes=payload.retry_delay_minutes,
    )
    session.add(schedule)
    await session.commit()
    await session.refresh(schedule)

    logger.info("schedule_created", schedule_id=str(schedule.id), cron=payload.cron_expression)
    return schedule


@router.get("", response_model=list[ScheduleResponse])
async def list_schedules(
    url_id: uuid.UUID | None = Query(default=None),
    is_active: bool | None = Query(default=None),
    session: AsyncSession = Depends(get_db),
) -> list[Schedule]:
    """스케줄 목록을 조회합니다."""
    query = select(Schedule).order_by(Schedule.created_at.desc())
    if url_id:
        query = query.where(Schedule.url_id == url_id)
    if is_active is not None:
        query = query.where(Schedule.is_active == is_active)

    result = await session.execute(query)
    return list(result.scalars().all())


@router.get("/{schedule_id}", response_model=ScheduleResponse)
async def get_schedule(schedule_id: uuid.UUID, session: AsyncSession = Depends(get_db)) -> Schedule:
    result = await session.execute(select(Schedule).where(Schedule.id == schedule_id))
    schedule = result.scalar_one_or_none()
    if not schedule:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="스케줄을 찾을 수 없습니다.")
    return schedule


@router.put("/{schedule_id}", response_model=ScheduleResponse)
async def update_schedule(
    schedule_id: uuid.UUID,
    payload: ScheduleUpdate,
    session: AsyncSession = Depends(get_db),
) -> Schedule:
    """스케줄을 수정합니다."""
    result = await session.execute(select(Schedule).where(Schedule.id == schedule_id))
    schedule = result.scalar_one_or_none()
    if not schedule:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="스케줄을 찾을 수 없습니다.")

    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(schedule, field, value)

    await session.commit()
    await session.refresh(schedule)
    return schedule


@router.delete("/{schedule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_schedule(schedule_id: uuid.UUID, session: AsyncSession = Depends(get_db)) -> None:
    result = await session.execute(select(Schedule).where(Schedule.id == schedule_id))
    schedule = result.scalar_one_or_none()
    if not schedule:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="스케줄을 찾을 수 없습니다.")

    await session.delete(schedule)
    await session.commit()


@router.post("/{schedule_id}/pause", response_model=ScheduleResponse)
async def pause_schedule(schedule_id: uuid.UUID, session: AsyncSession = Depends(get_db)) -> Schedule:
    """스케줄을 일시정지합니다."""
    result = await session.execute(select(Schedule).where(Schedule.id == schedule_id))
    schedule = result.scalar_one_or_none()
    if not schedule:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="스케줄을 찾을 수 없습니다.")

    schedule.is_active = False
    await session.commit()
    await session.refresh(schedule)
    return schedule


@router.post("/{schedule_id}/resume", response_model=ScheduleResponse)
async def resume_schedule(schedule_id: uuid.UUID, session: AsyncSession = Depends(get_db)) -> Schedule:
    """스케줄을 재개합니다."""
    result = await session.execute(select(Schedule).where(Schedule.id == schedule_id))
    schedule = result.scalar_one_or_none()
    if not schedule:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="스케줄을 찾을 수 없습니다.")

    schedule.is_active = True
    await session.commit()
    await session.refresh(schedule)
    return schedule


@router.post("/{schedule_id}/run", status_code=status.HTTP_202_ACCEPTED)
async def run_schedule_now(schedule_id: uuid.UUID, session: AsyncSession = Depends(get_db)) -> dict:
    """스케줄을 즉시 실행합니다."""
    result = await session.execute(select(Schedule).where(Schedule.id == schedule_id))
    schedule = result.scalar_one_or_none()
    if not schedule:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="스케줄을 찾을 수 없습니다.")

    # Phase 3에서 Celery task로 연동
    logger.info("schedule_run_now", schedule_id=str(schedule_id), url_id=str(schedule.url_id))
    return {"message": "즉시 실행 요청이 접수되었습니다.", "schedule_id": str(schedule_id)}
