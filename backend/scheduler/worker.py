"""Celery 워커 및 태스크 큐 설정."""
from celery import Celery

from backend.config import get_settings

settings = get_settings()

celery_app = Celery(
    "smart_web_scraper",
    broker=settings.redis_broker_url,
    backend=settings.redis_url,
    include=["backend.scheduler.tasks"],
)

celery_app.conf.update(
    # 시리얼라이저
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    # 시간대
    timezone="Asia/Seoul",
    enable_utc=True,
    # 재시도 정책
    task_max_retries=3,
    task_default_retry_delay=60,
    task_acks_late=True,
    # 큐 라우팅
    task_routes={
        "backend.scheduler.tasks.scrape_url_task": {"queue": "scrape_medium"},
        "backend.scheduler.tasks.scrape_high_priority_task": {"queue": "scrape_high"},
        "backend.scheduler.tasks.scrape_proxy_task": {"queue": "scrape_low"},
        "backend.scheduler.tasks.heal_task": {"queue": "heal"},
        "backend.scheduler.tasks.send_notification_task": {"queue": "notify"},
    },
    # 큐 정의
    task_queues={
        "scrape_high": {"exchange": "scrape_high", "routing_key": "scrape.high"},
        "scrape_medium": {"exchange": "scrape_medium", "routing_key": "scrape.medium"},
        "scrape_low": {"exchange": "scrape_low", "routing_key": "scrape.low"},
        "heal": {"exchange": "heal", "routing_key": "heal"},
        "notify": {"exchange": "notify", "routing_key": "notify"},
    },
    # 워커 설정
    worker_prefetch_multiplier=4,
    worker_max_tasks_per_child=100,  # 메모리 누수 방지
    # 결과 보존 기간 (1일)
    result_expires=86400,
    # Beat 스케줄 (APScheduler로 대체되지만 기본 설정)
    beat_schedule={},
)
