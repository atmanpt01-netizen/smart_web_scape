import uuid
from datetime import datetime

from sqlalchemy import (
    JSON,
    ARRAY,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Url(Base):
    __tablename__ = "urls"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    url: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    name: Mapped[str | None] = mapped_column(String(255))
    domain: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False, default="enterprise")
    extraction_schema: Mapped[dict | None] = mapped_column(JSONB)
    auth_config: Mapped[dict | None] = mapped_column(JSONB)  # AES-256-GCM encrypted
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    tags: Mapped[list[str] | None] = mapped_column(ARRAY(Text))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    profile: Mapped["UrlProfile | None"] = relationship("UrlProfile", back_populates="url_obj", uselist=False)
    visit_logs: Mapped[list["VisitLog"]] = relationship("VisitLog", back_populates="url_obj")
    schedules: Mapped[list["Schedule"]] = relationship("Schedule", back_populates="url_obj")
    scraped_data: Mapped[list["ScrapedData"]] = relationship("ScrapedData", back_populates="url_obj")
    alerts: Mapped[list["Alert"]] = relationship("Alert", back_populates="url_obj")


class UrlProfile(Base):
    __tablename__ = "url_profiles"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    url_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("urls.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    domain: Mapped[str] = mapped_column(String(255), nullable=False)

    # Learned optimal strategy
    best_pipeline: Mapped[str | None] = mapped_column(String(50))
    best_user_agent: Mapped[str | None] = mapped_column(Text)
    best_headers: Mapped[dict | None] = mapped_column(JSONB)
    optimal_delay_ms: Mapped[int] = mapped_column(Integer, default=1000)

    # Statistics
    total_visits: Mapped[int] = mapped_column(Integer, default=0)
    success_count: Mapped[int] = mapped_column(Integer, default=0)
    success_rate: Mapped[float] = mapped_column(Float, default=0.0)
    avg_response_time_ms: Mapped[float] = mapped_column(Float, default=0.0)

    # Site characteristics
    requires_js: Mapped[bool] = mapped_column(Boolean, default=False)
    has_antibot: Mapped[bool] = mapped_column(Boolean, default=False)
    antibot_type: Mapped[str | None] = mapped_column(String(100))
    has_api: Mapped[bool] = mapped_column(Boolean, default=False)
    api_endpoint: Mapped[str | None] = mapped_column(Text)

    # Structure info (for healing)
    page_structure_hash: Mapped[str | None] = mapped_column(String(64))
    last_selectors: Mapped[dict | None] = mapped_column(JSONB)
    selector_history: Mapped[list] = mapped_column(JSONB, default=list)

    last_visited_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationship
    url_obj: Mapped["Url"] = relationship("Url", back_populates="profile")


class VisitLog(Base):
    __tablename__ = "visit_logs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    url_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("urls.id", ondelete="CASCADE"), nullable=False
    )
    url: Mapped[str] = mapped_column(Text, nullable=False)
    visited_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Performance
    duration_ms: Mapped[int | None] = mapped_column(Integer)

    # Results
    success: Mapped[bool] = mapped_column(Boolean, nullable=False)
    status_code: Mapped[int | None] = mapped_column(Integer)
    error_type: Mapped[str | None] = mapped_column(String(100))
    error_message: Mapped[str | None] = mapped_column(Text)

    # Pipeline info
    pipeline_name: Mapped[str] = mapped_column(String(50), nullable=False)
    pipeline_sequence: Mapped[int | None] = mapped_column(Integer)
    pipelines_attempted: Mapped[list[str] | None] = mapped_column(ARRAY(Text))
    method_details: Mapped[dict | None] = mapped_column(JSONB)
    proxy_used: Mapped[str | None] = mapped_column(String(255))

    # Collection results
    content_hash: Mapped[str | None] = mapped_column(String(64))
    content_size_bytes: Mapped[int | None] = mapped_column(Integer)
    items_extracted: Mapped[int | None] = mapped_column(Integer)

    # Anti-bot tracking
    antibot_detected: Mapped[str | None] = mapped_column(String(100))
    captcha_encountered: Mapped[bool] = mapped_column(Boolean, default=False)
    captcha_solved: Mapped[bool] = mapped_column(Boolean, default=False)
    healing_applied: Mapped[bool] = mapped_column(Boolean, default=False)
    healing_type: Mapped[str | None] = mapped_column(String(100))

    # Relationships
    url_obj: Mapped["Url"] = relationship("Url", back_populates="visit_logs")
    scraped_data: Mapped[list["ScrapedData"]] = relationship("ScrapedData", back_populates="visit_log")

    __table_args__ = (
        Index("idx_visit_logs_time", "visited_at"),
        Index("idx_visit_logs_url", "url_id", "visited_at"),
        Index("idx_visit_logs_success", "success", "visited_at"),
    )


class Schedule(Base):
    __tablename__ = "schedules"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    url_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("urls.id", ondelete="CASCADE"), nullable=False
    )
    schedule_type: Mapped[str] = mapped_column(String(20), nullable=False)  # hourly|daily|weekly|monthly|custom
    cron_expression: Mapped[str] = mapped_column(String(100), nullable=False)
    timezone: Mapped[str] = mapped_column(String(50), default="Asia/Seoul")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    max_retries: Mapped[int] = mapped_column(Integer, default=3)
    retry_delay_minutes: Mapped[int] = mapped_column(Integer, default=5)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    next_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    run_count: Mapped[int] = mapped_column(Integer, default=0)
    success_count: Mapped[int] = mapped_column(Integer, default=0)
    failure_count: Mapped[int] = mapped_column(Integer, default=0)

    # Relationship
    url_obj: Mapped["Url"] = relationship("Url", back_populates="schedules")


class ScrapedData(Base):
    __tablename__ = "scraped_data"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    url_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("urls.id", ondelete="CASCADE"), nullable=False
    )
    visit_log_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("visit_logs.id", ondelete="SET NULL")
    )
    data: Mapped[dict] = mapped_column(JSONB, nullable=False)
    raw_content: Mapped[str | None] = mapped_column(Text)
    content_hash: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    url_obj: Mapped["Url"] = relationship("Url", back_populates="scraped_data")
    visit_log: Mapped["VisitLog | None"] = relationship("VisitLog", back_populates="scraped_data")

    __table_args__ = (Index("idx_scraped_data_url", "url_id", "created_at"),)


class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    url_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("urls.id", ondelete="SET NULL")
    )
    severity: Mapped[str] = mapped_column(String(20), nullable=False)  # info|warning|error|critical
    alert_type: Mapped[str] = mapped_column(String(100), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relationship
    url_obj: Mapped["Url | None"] = relationship("Url", back_populates="alerts")
