import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, HttpUrl, field_validator


# ─── URL Schemas ───────────────────────────────────────────

class UrlCreate(BaseModel):
    url: str
    name: str | None = None
    category: str | None = None  # auto-detected if None
    extraction_schema: dict[str, str] | None = None
    auth_config: dict[str, Any] | None = None
    tags: list[str] | None = None

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        if not v.startswith(("http://", "https://")):
            raise ValueError("URL must start with http:// or https://")
        return v.rstrip("/")


class BulkUrlCreate(BaseModel):
    urls: list[UrlCreate]


class UrlUpdate(BaseModel):
    name: str | None = None
    category: str | None = None
    extraction_schema: dict[str, str] | None = None
    auth_config: dict[str, Any] | None = None
    tags: list[str] | None = None
    is_active: bool | None = None


class UrlResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    url: str
    name: str | None
    domain: str
    category: str
    extraction_schema: dict[str, str] | None
    is_active: bool
    tags: list[str] | None
    created_at: datetime
    updated_at: datetime


class UrlListResponse(BaseModel):
    items: list[UrlResponse]
    total: int
    page: int
    size: int
    pages: int


# ─── Scrape Schemas ────────────────────────────────────────

class ScrapeTask(BaseModel):
    url_id: uuid.UUID
    url: str
    category: str
    extraction_schema: dict[str, str] | None = None
    pipeline_override: str | None = None  # force specific pipeline


class ScrapeResult(BaseModel):
    url_id: uuid.UUID
    url: str
    success: bool
    pipeline_name: str
    pipeline_sequence: int
    pipelines_attempted: list[str]
    duration_ms: int
    status_code: int | None = None
    error_type: str | None = None
    error_message: str | None = None
    data: dict[str, Any] | None = None
    raw_content: str | None = None
    content_hash: str | None = None
    content_size_bytes: int | None = None
    items_extracted: int | None = None
    antibot_detected: str | None = None
    captcha_encountered: bool = False
    healing_applied: bool = False
    healing_type: str | None = None
    method_details: dict[str, Any] | None = None


class ScrapeRequest(BaseModel):
    url_id: uuid.UUID
    pipeline_override: str | None = None


class BulkScrapeRequest(BaseModel):
    url_ids: list[uuid.UUID]


class ScrapeStatusResponse(BaseModel):
    task_id: str
    status: str  # pending|running|success|failed|cancelled
    result: ScrapeResult | None = None
    created_at: datetime | None = None


# ─── Visit Log Schemas ────────────────────────────────────

class VisitLogResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    url_id: uuid.UUID
    url: str
    visited_at: datetime
    duration_ms: int | None
    success: bool
    status_code: int | None
    error_type: str | None
    error_message: str | None
    pipeline_name: str
    pipeline_sequence: int | None
    pipelines_attempted: list[str] | None
    content_hash: str | None
    content_size_bytes: int | None
    items_extracted: int | None
    antibot_detected: str | None
    captcha_encountered: bool
    healing_applied: bool
    healing_type: str | None


class VisitLogListResponse(BaseModel):
    items: list[VisitLogResponse]
    total: int
    page: int
    size: int
    pages: int


# ─── Schedule Schemas ─────────────────────────────────────

class ScheduleCreate(BaseModel):
    url_id: uuid.UUID
    schedule_type: str  # hourly|daily|weekly|monthly|custom
    cron_expression: str
    timezone: str = "Asia/Seoul"
    max_retries: int = 3
    retry_delay_minutes: int = 5


class ScheduleUpdate(BaseModel):
    schedule_type: str | None = None
    cron_expression: str | None = None
    timezone: str | None = None
    is_active: bool | None = None
    max_retries: int | None = None
    retry_delay_minutes: int | None = None


class ScheduleResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    url_id: uuid.UUID
    schedule_type: str
    cron_expression: str
    timezone: str
    is_active: bool
    max_retries: int
    retry_delay_minutes: int
    created_at: datetime
    last_run_at: datetime | None
    next_run_at: datetime | None
    run_count: int
    success_count: int
    failure_count: int


# ─── Alert Schemas ────────────────────────────────────────

class AlertResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    url_id: uuid.UUID | None
    severity: str
    alert_type: str
    message: str
    is_read: bool
    created_at: datetime
