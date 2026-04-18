import uuid
from datetime import datetime

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.schemas import ScrapeResult, VisitLogListResponse, VisitLogResponse
from backend.db.models import ScrapedData, VisitLog

logger = structlog.get_logger(__name__)


class VisitLogger:
    """방문 이력을 DB에 기록하고 조회합니다."""

    async def log(self, session: AsyncSession, result: ScrapeResult) -> VisitLog:
        """수집 결과를 visit_logs 테이블에 기록합니다."""
        visit_log = VisitLog(
            url_id=result.url_id,
            url=result.url,
            success=result.success,
            duration_ms=result.duration_ms,
            status_code=result.status_code,
            error_type=result.error_type,
            error_message=result.error_message,
            pipeline_name=result.pipeline_name,
            pipeline_sequence=result.pipeline_sequence,
            pipelines_attempted=result.pipelines_attempted,
            method_details=result.method_details,
            content_hash=result.content_hash,
            content_size_bytes=result.content_size_bytes,
            items_extracted=result.items_extracted,
            antibot_detected=result.antibot_detected,
            captcha_encountered=result.captcha_encountered,
            healing_applied=result.healing_applied,
            healing_type=result.healing_type,
        )
        session.add(visit_log)

        # 수집 데이터가 있으면 scraped_data에도 저장
        if result.success and result.data:
            scraped = ScrapedData(
                url_id=result.url_id,
                data=result.data,
                raw_content=result.raw_content,
                content_hash=result.content_hash,
            )
            session.add(scraped)
            await session.flush()
            scraped.visit_log_id = visit_log.id

        await session.commit()
        await session.refresh(visit_log)

        logger.info(
            "visit_logged",
            url_id=str(result.url_id),
            success=result.success,
            pipeline=result.pipeline_name,
            duration_ms=result.duration_ms,
        )
        return visit_log

    async def get_history(
        self,
        session: AsyncSession,
        page: int = 1,
        size: int = 20,
        url_id: uuid.UUID | None = None,
        success: bool | None = None,
        pipeline_name: str | None = None,
    ) -> VisitLogListResponse:
        """방문 이력 목록을 페이지네이션으로 조회합니다."""
        query = select(VisitLog).order_by(VisitLog.visited_at.desc())

        if url_id is not None:
            query = query.where(VisitLog.url_id == url_id)
        if success is not None:
            query = query.where(VisitLog.success == success)
        if pipeline_name:
            query = query.where(VisitLog.pipeline_name == pipeline_name)

        # 전체 카운트
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await session.execute(count_query)
        total = total_result.scalar_one()

        # 페이지네이션
        offset = (page - 1) * size
        result = await session.execute(query.offset(offset).limit(size))
        logs = result.scalars().all()

        pages = (total + size - 1) // size
        items = [VisitLogResponse.model_validate(log) for log in logs]

        return VisitLogListResponse(items=items, total=total, page=page, size=size, pages=pages)

    async def get_by_id(self, session: AsyncSession, log_id: uuid.UUID) -> VisitLog | None:
        result = await session.execute(select(VisitLog).where(VisitLog.id == log_id))
        return result.scalar_one_or_none()
