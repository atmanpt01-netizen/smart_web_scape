"""APScheduler 기반 스케줄 관리자."""
import uuid
from datetime import datetime

import structlog
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models import Schedule, Url

logger = structlog.get_logger(__name__)


class SchedulerManager:
    """APScheduler + Celery 연동 스케줄 매니저."""

    def __init__(self) -> None:
        self._scheduler = AsyncIOScheduler(timezone="Asia/Seoul")
        self._scheduler.start()
        logger.info("scheduler_started")

    async def register_schedule(self, session: AsyncSession, schedule: Schedule) -> None:
        """스케줄을 APScheduler에 등록합니다."""
        job_id = str(schedule.id)

        self._scheduler.add_job(
            func=self._trigger_scrape,
            trigger=CronTrigger.from_crontab(schedule.cron_expression, timezone=schedule.timezone),
            id=job_id,
            args=[str(schedule.url_id), str(schedule.id)],
            replace_existing=True,
            misfire_grace_time=300,  # 5분 내 실행 누락 허용
            coalesce=True,  # 누적 실행은 한 번만
        )

        # next_run_at 갱신
        job = self._scheduler.get_job(job_id)
        if job and job.next_run_time:
            schedule.next_run_at = job.next_run_time
            await session.commit()

        logger.info("schedule_registered", schedule_id=job_id, cron=schedule.cron_expression)

    async def pause_schedule(self, schedule_id: uuid.UUID) -> None:
        """스케줄을 일시정지합니다."""
        job_id = str(schedule_id)
        job = self._scheduler.get_job(job_id)
        if job:
            self._scheduler.pause_job(job_id)
            logger.info("schedule_paused", schedule_id=job_id)

    async def resume_schedule(self, schedule_id: uuid.UUID) -> None:
        """스케줄을 재개합니다."""
        job_id = str(schedule_id)
        job = self._scheduler.get_job(job_id)
        if job:
            self._scheduler.resume_job(job_id)
            logger.info("schedule_resumed", schedule_id=job_id)

    async def update_schedule(self, schedule_id: uuid.UUID, new_cron: str, timezone: str = "Asia/Seoul") -> None:
        """스케줄 cron 표현식을 업데이트합니다."""
        job_id = str(schedule_id)
        self._scheduler.reschedule_job(
            job_id,
            trigger=CronTrigger.from_crontab(new_cron, timezone=timezone),
        )
        logger.info("schedule_updated", schedule_id=job_id, new_cron=new_cron)

    async def delete_schedule(self, schedule_id: uuid.UUID) -> None:
        """스케줄을 APScheduler에서 제거합니다."""
        job_id = str(schedule_id)
        job = self._scheduler.get_job(job_id)
        if job:
            self._scheduler.remove_job(job_id)
            logger.info("schedule_deleted", schedule_id=job_id)

    async def execute_now(self, url_id: uuid.UUID, schedule_id: uuid.UUID | None = None) -> None:
        """스케줄을 즉시 실행합니다."""
        await self._trigger_scrape(str(url_id), str(schedule_id) if schedule_id else "manual")

    async def _trigger_scrape(self, url_id: str, schedule_id: str) -> None:
        """Celery 태스크를 통해 수집을 트리거합니다."""
        from backend.scheduler.tasks import scrape_url_task
        scrape_url_task.delay(url_id)
        logger.info("schedule_triggered", url_id=url_id, schedule_id=schedule_id)

    def shutdown(self) -> None:
        """스케줄러를 종료합니다."""
        self._scheduler.shutdown()


# 싱글턴
_scheduler_manager: SchedulerManager | None = None


def get_scheduler_manager() -> SchedulerManager:
    global _scheduler_manager
    if _scheduler_manager is None:
        _scheduler_manager = SchedulerManager()
    return _scheduler_manager
