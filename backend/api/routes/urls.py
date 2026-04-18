import csv
import io
import math
import uuid

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.schemas import (
    BulkUrlCreate,
    UrlCreate,
    UrlListResponse,
    UrlResponse,
    UrlUpdate,
)
from backend.core.url_classifier import classify_url, extract_domain
from backend.db.models import Url, UrlProfile
from backend.db.session import get_db
from backend.utils.robots_checker import check_robots_txt

router = APIRouter()
logger = structlog.get_logger(__name__)


async def _create_url(session: AsyncSession, url_data: UrlCreate) -> Url:
    """단일 URL을 DB에 등록합니다."""
    # 중복 확인
    existing = await session.execute(select(Url).where(Url.url == url_data.url))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"이미 등록된 URL입니다: {url_data.url}")

    # robots.txt 확인
    allowed = await check_robots_txt(url_data.url)
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"robots.txt에 의해 수집이 차단된 URL입니다: {url_data.url}",
        )

    domain = extract_domain(url_data.url)
    category = url_data.category or classify_url(url_data.url)

    url_obj = Url(
        url=url_data.url,
        name=url_data.name,
        domain=domain,
        category=category,
        extraction_schema=url_data.extraction_schema,
        auth_config=url_data.auth_config,
        tags=url_data.tags,
    )
    session.add(url_obj)
    await session.flush()

    # URL 프로파일 자동 생성
    profile = UrlProfile(url_id=url_obj.id, domain=domain)
    session.add(profile)

    await session.commit()
    await session.refresh(url_obj)
    return url_obj


@router.post("", response_model=UrlResponse | list[UrlResponse], status_code=status.HTTP_201_CREATED)
async def register_url(
    payload: UrlCreate | BulkUrlCreate,
    session: AsyncSession = Depends(get_db),
) -> Url | list[Url]:
    """단일 또는 복수 URL을 등록합니다."""
    if isinstance(payload, BulkUrlCreate):
        results = []
        errors = []
        for url_data in payload.urls:
            try:
                url_obj = await _create_url(session, url_data)
                results.append(url_obj)
            except HTTPException as e:
                errors.append({"url": url_data.url, "error": e.detail})
                await session.rollback()

        if errors and not results:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=errors)

        logger.info("bulk_urls_registered", count=len(results), errors=len(errors))
        return results
    else:
        return await _create_url(session, payload)


@router.get("", response_model=UrlListResponse)
async def list_urls(
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
    category: str | None = Query(default=None),
    is_active: bool | None = Query(default=None),
    search: str | None = Query(default=None),
    session: AsyncSession = Depends(get_db),
) -> UrlListResponse:
    """등록된 URL 목록을 조회합니다."""
    query = select(Url).order_by(Url.created_at.desc())

    if category:
        query = query.where(Url.category == category)
    if is_active is not None:
        query = query.where(Url.is_active == is_active)
    if search:
        search_pattern = f"%{search}%"
        query = query.where(
            or_(Url.url.ilike(search_pattern), Url.name.ilike(search_pattern))
        )

    count_query = select(func.count()).select_from(query.subquery())
    total = (await session.execute(count_query)).scalar_one()

    offset = (page - 1) * size
    result = await session.execute(query.offset(offset).limit(size))
    urls = result.scalars().all()

    pages = math.ceil(total / size) if total > 0 else 1
    items = [UrlResponse.model_validate(u) for u in urls]
    return UrlListResponse(items=items, total=total, page=page, size=size, pages=pages)


@router.get("/{url_id}", response_model=UrlResponse)
async def get_url(url_id: uuid.UUID, session: AsyncSession = Depends(get_db)) -> Url:
    """특정 URL 상세 정보를 조회합니다."""
    result = await session.execute(select(Url).where(Url.id == url_id))
    url_obj = result.scalar_one_or_none()
    if not url_obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="URL을 찾을 수 없습니다.")
    return url_obj


@router.put("/{url_id}", response_model=UrlResponse)
async def update_url(
    url_id: uuid.UUID,
    payload: UrlUpdate,
    session: AsyncSession = Depends(get_db),
) -> Url:
    """URL 설정을 수정합니다."""
    result = await session.execute(select(Url).where(Url.id == url_id))
    url_obj = result.scalar_one_or_none()
    if not url_obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="URL을 찾을 수 없습니다.")

    update_data = payload.model_dump(exclude_none=True)
    for field, value in update_data.items():
        setattr(url_obj, field, value)

    await session.commit()
    await session.refresh(url_obj)
    return url_obj


@router.delete("/{url_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_url(url_id: uuid.UUID, session: AsyncSession = Depends(get_db)) -> None:
    """URL을 삭제합니다 (CASCADE: 프로파일, 방문 이력, 스케줄, 수집 데이터 모두 삭제)."""
    result = await session.execute(select(Url).where(Url.id == url_id))
    url_obj = result.scalar_one_or_none()
    if not url_obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="URL을 찾을 수 없습니다.")

    await session.delete(url_obj)
    await session.commit()
    logger.info("url_deleted", url_id=str(url_id), url=url_obj.url)


@router.post("/import", response_model=dict, status_code=status.HTTP_201_CREATED)
async def import_urls_csv(
    file: UploadFile,
    session: AsyncSession = Depends(get_db),
) -> dict:
    """CSV 파일에서 URL을 일괄 가져옵니다.

    CSV 컬럼: url (필수), name (선택), category (선택)
    """
    if not file.filename or not file.filename.endswith(".csv"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="CSV 파일만 업로드 가능합니다.")

    content = await file.read()
    text = content.decode("utf-8-sig")  # BOM 처리

    reader = csv.DictReader(io.StringIO(text))
    if "url" not in (reader.fieldnames or []):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="CSV에 'url' 컬럼이 필요합니다.",
        )

    success_count = 0
    error_list = []

    for row in reader:
        url_str = row.get("url", "").strip()
        if not url_str:
            continue

        url_data = UrlCreate(
            url=url_str,
            name=row.get("name") or None,
            category=row.get("category") or None,
        )
        try:
            await _create_url(session, url_data)
            success_count += 1
        except HTTPException as e:
            error_list.append({"url": url_str, "error": e.detail})
            await session.rollback()

    return {
        "registered": success_count,
        "errors": len(error_list),
        "error_details": error_list,
    }
