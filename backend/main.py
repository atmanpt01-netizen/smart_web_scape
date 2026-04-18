import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.routes import auth, dashboard, history, schedules, scrape, urls, websocket
from backend.config import get_settings
from backend.db.session import engine

logger = structlog.get_logger(__name__)

settings = get_settings()

app = FastAPI(
    title="Smart Web Scraper API",
    description="지능형 웹 데이터 수집 플랫폼 — 5단계 적응형 파이프라인 + Self-Healing",
    version="0.1.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API 라우터 등록
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Auth"])
app.include_router(urls.router, prefix="/api/v1/urls", tags=["URLs"])
app.include_router(scrape.router, prefix="/api/v1/scrape", tags=["Scrape"])
app.include_router(schedules.router, prefix="/api/v1/schedules", tags=["Schedules"])
app.include_router(dashboard.router, prefix="/api/v1/dashboard", tags=["Dashboard"])
app.include_router(history.router, prefix="/api/v1/history", tags=["History"])

# WebSocket
app.include_router(websocket.router, prefix="/ws", tags=["WebSocket"])


@app.on_event("startup")
async def startup_event() -> None:
    logger.info("app_starting", env=settings.app_env)
    # DB 연결 확인
    try:
        async with engine.connect() as conn:
            await conn.execute(__import__("sqlalchemy").text("SELECT 1"))
        logger.info("database_connected")
    except Exception as e:
        logger.error("database_connection_failed", error=str(e))


@app.on_event("shutdown")
async def shutdown_event() -> None:
    logger.info("app_shutting_down")
    await engine.dispose()


@app.get("/health", tags=["Health"])
async def health_check() -> dict:
    """헬스 체크 엔드포인트."""
    return {"status": "ok", "version": "0.1.0"}
