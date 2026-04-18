import asyncio
import uuid
from datetime import datetime

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.schemas import (
    BulkScrapeRequest,
    ScrapeRequest,
    ScrapeResult,
    ScrapeStatusResponse,
    ScrapeTask,
)
from backend.core.orchestrator import PipelineOrchestrator
from backend.db.models import Url
from backend.db.session import get_db
from backend.logger.visit_logger import VisitLogger

router = APIRouter()
logger = structlog.get_logger(__name__)

_orchestrator = PipelineOrchestrator()
_visit_logger = VisitLogger()

# 인메모리 태스크 상태 저장소 (Phase 3에서 Redis로 전환)
_task_store: dict[str, dict] = {}


async def _run_scrape(task_id: str, task: ScrapeTask, session: AsyncSession) -> None:
    """수집 작업을 실행하고 결과를 저장합니다."""
    _task_store[task_id] = {"status": "running", "created_at": datetime.utcnow()}

    result = await _orchestrator.execute(task)

    await _visit_logger.log(session, result)

    _task_store[task_id] = {
        "status": "success" if result.success else "failed",
        "result": result,
        "created_at": _task_store[task_id]["created_at"],
    }


@router.post("/now", response_model=ScrapeStatusResponse, status_code=status.HTTP_202_ACCEPTED)
async def scrape_now(
    payload: ScrapeRequest,
    session: AsyncSession = Depends(get_db),
) -> ScrapeStatusResponse:
    """URL을 즉시 수집합니다 (비동기 실행)."""
    # URL 조회
    result = await session.execute(select(Url).where(Url.id == payload.url_id))
    url_obj = result.scalar_one_or_none()
    if not url_obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="URL을 찾을 수 없습니다.")
    if not url_obj.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="비활성화된 URL입니다.")

    task_id = str(uuid.uuid4())
    task = ScrapeTask(
        url_id=url_obj.id,
        url=url_obj.url,
        category=url_obj.category,
        extraction_schema=url_obj.extraction_schema,
        pipeline_override=payload.pipeline_override,
    )

    # 백그라운드 실행 (Phase 3에서 Celery로 전환)
    asyncio.create_task(_run_scrape(task_id, task, session))

    logger.info("scrape_triggered", task_id=task_id, url=url_obj.url)
    return ScrapeStatusResponse(task_id=task_id, status="pending", created_at=datetime.utcnow())


@router.post("/bulk", status_code=status.HTTP_202_ACCEPTED)
async def scrape_bulk(
    payload: BulkScrapeRequest,
    session: AsyncSession = Depends(get_db),
) -> dict:
    """여러 URL을 일괄 수집합니다 (최대 50개 병렬 실행)."""
    if len(payload.url_ids) > 50:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="한 번에 최대 50개 URL만 수집 가능합니다.",
        )

    # URL 조회
    result = await session.execute(select(Url).where(Url.id.in_(payload.url_ids), Url.is_active.is_(True)))
    urls = result.scalars().all()

    task_ids = []
    for url_obj in urls:
        task_id = str(uuid.uuid4())
        task = ScrapeTask(
            url_id=url_obj.id,
            url=url_obj.url,
            category=url_obj.category,
            extraction_schema=url_obj.extraction_schema,
        )
        asyncio.create_task(_run_scrape(task_id, task, session))
        task_ids.append(task_id)

    logger.info("bulk_scrape_triggered", count=len(task_ids))
    return {"task_ids": task_ids, "count": len(task_ids)}


@router.get("/{task_id}/status", response_model=ScrapeStatusResponse)
async def get_scrape_status(task_id: str) -> ScrapeStatusResponse:
    """수집 작업의 현재 상태를 조회합니다."""
    task_data = _task_store.get(task_id)
    if not task_data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="태스크를 찾을 수 없습니다.")

    return ScrapeStatusResponse(
        task_id=task_id,
        status=task_data["status"],
        result=task_data.get("result"),
        created_at=task_data.get("created_at"),
    )


@router.post("/{task_id}/cancel", status_code=status.HTTP_200_OK)
async def cancel_scrape(task_id: str) -> dict:
    """수집 작업을 취소합니다."""
    task_data = _task_store.get(task_id)
    if not task_data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="태스크를 찾을 수 없습니다.")

    if task_data["status"] in ("success", "failed", "cancelled"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"이미 완료된 태스크입니다: {task_data['status']}")

    _task_store[task_id]["status"] = "cancelled"
    logger.info("scrape_cancelled", task_id=task_id)
    return {"task_id": task_id, "status": "cancelled"}
