import csv
import io
import uuid

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.schemas import VisitLogListResponse, VisitLogResponse
from backend.db.session import get_db
from backend.logger.visit_logger import VisitLogger

router = APIRouter()
logger = structlog.get_logger(__name__)
_visit_logger = VisitLogger()


@router.get("", response_model=VisitLogListResponse)
async def list_history(
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
    url_id: uuid.UUID | None = Query(default=None),
    success: bool | None = Query(default=None),
    pipeline_name: str | None = Query(default=None),
    session: AsyncSession = Depends(get_db),
) -> VisitLogListResponse:
    """방문 이력 목록을 조회합니다."""
    return await _visit_logger.get_history(
        session=session,
        page=page,
        size=size,
        url_id=url_id,
        success=success,
        pipeline_name=pipeline_name,
    )


@router.get("/export")
async def export_history(
    format: str = Query(default="csv", pattern="^(csv|json)$"),
    url_id: uuid.UUID | None = Query(default=None),
    session: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    """방문 이력을 CSV 또는 JSON으로 내보냅니다."""
    # 전체 조회 (페이지네이션 없이)
    result = await _visit_logger.get_history(
        session=session,
        page=1,
        size=10000,
        url_id=url_id,
    )

    if format == "csv":
        output = io.StringIO()
        fieldnames = [
            "id", "url", "visited_at", "success", "pipeline_name",
            "duration_ms", "status_code", "error_type", "items_extracted",
        ]
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        for item in result.items:
            writer.writerow({
                "id": str(item.id),
                "url": item.url,
                "visited_at": item.visited_at.isoformat(),
                "success": item.success,
                "pipeline_name": item.pipeline_name,
                "duration_ms": item.duration_ms,
                "status_code": item.status_code,
                "error_type": item.error_type,
                "items_extracted": item.items_extracted,
            })

        output.seek(0)
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=visit_history.csv"},
        )
    else:
        import json
        data = [item.model_dump(mode="json") for item in result.items]
        return StreamingResponse(
            iter([json.dumps(data, ensure_ascii=False, indent=2)]),
            media_type="application/json",
            headers={"Content-Disposition": "attachment; filename=visit_history.json"},
        )


@router.get("/{log_id}", response_model=VisitLogResponse)
async def get_history_detail(
    log_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
) -> VisitLogResponse:
    """방문 이력 단건 상세를 조회합니다."""
    log = await _visit_logger.get_by_id(session, log_id)
    if not log:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="방문 이력을 찾을 수 없습니다.")
    return VisitLogResponse.model_validate(log)
