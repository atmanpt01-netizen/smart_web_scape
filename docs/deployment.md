# Deployment Guide

## Prerequisites

- Docker 27+ and Docker Compose v2
- 8 GB RAM minimum (16 GB recommended with Ollama AI pipeline)
- NVIDIA GPU (optional, for Ollama acceleration)

## Quick Start

```bash
# 1. Clone and navigate
cd smart-web-scraper

# 2. Copy and configure environment variables
cp .env.example .env
# Edit .env: set DATABASE_URL, REDIS_URL, SECRET_KEY, etc.

# 3. Start core stack (no AI pipeline)
docker compose up -d

# 4. Run database migrations
docker compose exec backend alembic upgrade head

# 5. Access the UI
open http://localhost
```

## Start with AI Pipeline (Ollama)

```bash
# Requires an NVIDIA GPU or sufficient RAM (≥8 GB for llama3.2:8b)
docker compose --profile ai up -d

# Pull the LLM model (first time only, ~4-5 GB)
docker compose exec ollama ollama pull llama3.2:8b
```

## Environment Variables Reference

| Variable | Required | Default | Description |
|---|---|---|---|
| `DATABASE_URL` | Yes | postgresql+asyncpg://... | PostgreSQL async connection string |
| `REDIS_URL` | Yes | redis://localhost:6379/0 | Redis connection for caching |
| `REDIS_BROKER_URL` | Yes | redis://localhost:6379/1 | Redis broker for Celery |
| `SECRET_KEY` | Yes | — | 64+ char random string for JWT signing |
| `OLLAMA_URL` | No | http://ollama:11434 | Ollama API endpoint |
| `SLACK_WEBHOOK_URL` | No | — | Slack incoming webhook for alerts |
| `SMTP_HOST` | No | smtp.gmail.com | SMTP server for email alerts |
| `DATA_GO_KR_API_KEY` | No | — | 공공데이터포털 API key |
| `NAVER_CLIENT_ID` | No | — | Naver Search API client ID |
| `KAKAO_REST_API_KEY` | No | — | Kakao REST API key |
| `DART_API_KEY` | No | — | DART 기업공시 API key |
| `PROXY_POOL_URL` | No | — | HTTP proxy pool URL |

## Services

| Service | Port | Description |
|---|---|---|
| nginx | 80/443 | Reverse proxy (entry point) |
| backend | 8000 | FastAPI application |
| worker | — | Celery worker (scrape_high/medium/low/heal queues) |
| beat | — | Celery Beat scheduler |
| frontend | 3000 | Vite React dev / nginx prod |
| postgres | 5432 | PostgreSQL 17 |
| redis | 6379 | Redis 7 |
| ollama | 11434 | Ollama LLM server (profile: ai) |

## Production Hardening

### Generate a secure SECRET_KEY
```bash
python -c "import secrets; print(secrets.token_hex(64))"
```

### SSL/TLS
Place your SSL certificates in `nginx/ssl/`:
- `nginx/ssl/cert.pem`
- `nginx/ssl/key.pem`

Then update `nginx/nginx.conf` to enable the HTTPS server block.

### Scaling Workers
```bash
# Scale to 4 worker replicas
docker compose up -d --scale worker=4
```

### Database Backup
```bash
docker compose exec postgres pg_dump -U scraper scraper_db > backup_$(date +%Y%m%d).sql
```

## Monitoring

- API docs: `http://localhost/api/docs`
- ReDoc: `http://localhost/api/redoc`
- Health check: `http://localhost/health`

## Updating

```bash
git pull
docker compose build
docker compose up -d
docker compose exec backend alembic upgrade head
```
