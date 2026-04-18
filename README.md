# Smart Web Scraper

지능형 웹 데이터 수집 플랫폼 — 5단계 적응형 파이프라인 + Self-Healing

## Features

- **5-Stage Adaptive Pipeline**: API → HTTP → Stealth Browser → AI Extraction → Proxy+Browser, auto-fallback
- **Self-Healing Engine**: Automatically repairs broken selectors, detects structural changes, rotates fingerprints
- **Scheduling**: Cron-based automatic scheduling with APScheduler + Celery
- **Real-time Dashboard**: WebSocket live feed, Recharts analytics, KPI cards
- **Korean-focused**: Government, finance, news, portal, SNS, e-commerce, enterprise categorization
- **URL Management**: Bulk import, auto-categorization, robots.txt compliance

## Quick Start

```bash
cd smart-web-scraper
cp .env.example .env
docker compose up -d
docker compose exec backend alembic upgrade head
# Open http://localhost
```

See [docs/deployment.md](docs/deployment.md) for detailed setup.

## Architecture

```
nginx:80 → backend:8000 (FastAPI)
         → frontend:3000 (React)
         → /ws/* (WebSocket)

backend → postgres:5432
        → redis:6379 (cache + Celery broker)
        → ollama:11434 (AI pipeline, optional)

Celery worker (scrape_high / scrape_medium / scrape_low / heal / notify)
Celery beat (APScheduler cron triggers)
```

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.12, FastAPI 0.115, SQLAlchemy 2.0, Alembic |
| Task Queue | Celery 5.4, Redis 7 |
| Scheduling | APScheduler 3.10, croniter |
| Scraping | httpx, curl_cffi, Playwright 1.49, Crawl4AI, Ollama |
| Database | PostgreSQL 17, asyncpg |
| Frontend | React 19, TypeScript 5.7, Vite 6, TanStack Query 5 |
| Charts | Recharts 2 |
| Styling | Tailwind CSS 4 |
| Infrastructure | Docker Compose, nginx 1.27 |

## Development

```bash
# Backend
cd smart-web-scraper
uv sync --dev
uv run uvicorn backend.main:app --reload --port 8000

# Frontend
cd smart-web-scraper/frontend
npm install
npm run dev

# Tests
uv run pytest tests/ -v --cov=backend

# Lint
uv run ruff check backend/
uv run ruff format backend/
uv run mypy backend/
```

## API Documentation

- Swagger UI: `http://localhost:8000/api/docs`
- ReDoc: `http://localhost:8000/api/redoc`

## Default Credentials

| Username | Password |
|---|---|
| admin | admin1234 |

**Change the default password and `SECRET_KEY` before deploying to production.**

## Pipeline Details

| Priority | Pipeline | Use Case |
|---|---|---|
| 1 | API | Official APIs (Naver, Kakao, DART, data.go.kr) |
| 2 | HTTP | Standard httpx + BeautifulSoup4, curl_cffi fallback |
| 3 | Stealth Browser | Playwright with anti-bot evasion |
| 4 | AI Extraction | Crawl4AI + Ollama LLM |
| 5 | Proxy + Browser | Full TLS fingerprint rotation + proxy pool |

## Self-Healing Levels

| Level | Trigger | Action |
|---|---|---|
| L1 | Selector not found | Fuzzy match, LLM-suggested selectors |
| L2 | Structure changed | DOM diffing, Ollama-based re-extraction |
| L3 | Blocked / Anti-bot | UA rotation, TLS profile change, proxy switch |
| L4 | CAPTCHA | 2Captcha / CapSolver (Phase 5) |
| L5 | Persistent failure | Alternative entry points (RSS, cache) |
