"""Celery 태스크 정의."""
import asyncio
from typing import Any

import structlog

from backend.scheduler.worker import celery_app

logger = structlog.get_logger(__name__)


def _run_async(coro: Any) -> Any:
    """동기 Celery 태스크에서 비동기 코루틴을 실행합니다."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(
    name="backend.scheduler.tasks.scrape_url_task",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def scrape_url_task(self: Any, url_id: str) -> dict:
    """단일 URL 수집 태스크."""
    from backend.core.orchestrator import PipelineOrchestrator
    from backend.api.schemas import ScrapeTask
    from backend.db.session import AsyncSessionLocal
    from backend.db.models import Url
    from sqlalchemy import select

    async def _execute() -> dict:
        orchestrator = PipelineOrchestrator()
        async with AsyncSessionLocal() as session:
            import uuid
            result = await session.execute(select(Url).where(Url.id == uuid.UUID(url_id)))
            url_obj = result.scalar_one_or_none()
            if not url_obj:
                return {"success": False, "error": "URL을 찾을 수 없습니다."}

            task = ScrapeTask(
                url_id=url_obj.id,
                url=url_obj.url,
                category=url_obj.category,
                extraction_schema=url_obj.extraction_schema,
            )
            scrape_result = await orchestrator.execute(task)

            from backend.logger.visit_logger import VisitLogger
            visit_logger = VisitLogger()
            await visit_logger.log(session, scrape_result)

            return {"success": scrape_result.success, "url": scrape_result.url}

    try:
        return _run_async(_execute())
    except Exception as exc:
        logger.error("scrape_task_failed", url_id=url_id, error=str(exc))
        raise self.retry(exc=exc)


@celery_app.task(
    name="backend.scheduler.tasks.scrape_high_priority_task",
    bind=True,
    max_retries=3,
    default_retry_delay=30,
)
def scrape_high_priority_task(self: Any, url_id: str) -> dict:
    """고우선순위 수집 태스크 (API 파이프라인 우선)."""
    return scrape_url_task.apply(args=[url_id]).get()


@celery_app.task(
    name="backend.scheduler.tasks.send_notification_task",
    bind=True,
    max_retries=2,
    default_retry_delay=30,
)
def send_notification_task(self: Any, alert_data: dict) -> None:
    """알림 전송 태스크."""
    from backend.utils.notifier import NotificationService

    async def _send() -> None:
        notifier = NotificationService()
        await notifier.send_alert(alert_data)

    try:
        _run_async(_send())
    except Exception as exc:
        logger.error("notification_task_failed", error=str(exc))
        raise self.retry(exc=exc)
