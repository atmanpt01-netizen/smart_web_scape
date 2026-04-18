"""Pipeline 3: Stealth Browser

Playwright + 스텔스 패치로 안티봇 탐지를 우회합니다.
User-Agent 순환, Geolocation/Timezone 스푸핑, navigator.webdriver=false 적용.
"""
import asyncio
import time
from typing import Any

import structlog
import xxhash

from backend.api.schemas import ScrapeResult, ScrapeTask
from backend.pipelines.base import BasePipeline
from backend.utils.user_agents import get_random_user_agent

logger = structlog.get_logger(__name__)

# 브라우저 풀 설정
BROWSER_POOL_SIZE = 10
MAX_CONTEXTS_PER_BROWSER = 5
CONTEXT_IDLE_TIMEOUT = 30  # seconds
REQUESTS_PER_BROWSER = 100  # 브라우저 재생성 주기


class StealthPipeline(BasePipeline):
    """Pipeline 3: Playwright Stealth Browser."""

    name = "stealth"
    priority = 3
    estimated_cost = 0.5
    avg_response_time = 8.0

    def __init__(self) -> None:
        self._request_count: dict[int, int] = {}

    async def execute(self, task: ScrapeTask) -> ScrapeResult:
        start_time = time.monotonic()
        pipelines_attempted = ["stealth"]

        try:
            from playwright.async_api import async_playwright

            async with async_playwright() as p:
                browser = await p.chromium.launch(
                    headless=True,
                    args=[
                        "--no-sandbox",
                        "--disable-setuid-sandbox",
                        "--disable-dev-shm-usage",
                        "--disable-blink-features=AutomationControlled",
                    ],
                )
                context = await browser.new_context(
                    user_agent=get_random_user_agent(),
                    locale="ko-KR",
                    timezone_id="Asia/Seoul",
                    geolocation={"latitude": 37.5665, "longitude": 126.9780},  # Seoul
                    permissions=["geolocation"],
                    viewport={"width": 1920, "height": 1080},
                    extra_http_headers={"Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8"},
                )

                # navigator.webdriver = false
                await context.add_init_script("""
                    Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
                    Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
                    Object.defineProperty(navigator, 'languages', { get: () => ['ko-KR', 'ko', 'en-US', 'en'] });
                """)

                page = await context.new_page()

                # 안티봇 탐지 패턴 차단
                await page.route("**/*.{png,jpg,jpeg,gif,svg,ico,woff,woff2}", lambda r: r.abort())

                response = await page.goto(task.url, wait_until="networkidle", timeout=30000)

                antibot_detected = None
                if response and response.status in (403, 429, 503):
                    antibot_detected = f"stealth_{response.status}"

                if response and response.status not in range(200, 300):
                    await browser.close()
                    duration_ms = int((time.monotonic() - start_time) * 1000)
                    return ScrapeResult(
                        url_id=task.url_id,
                        url=task.url,
                        success=False,
                        pipeline_name=self.name,
                        pipeline_sequence=self.priority,
                        pipelines_attempted=pipelines_attempted,
                        duration_ms=duration_ms,
                        status_code=response.status if response else None,
                        error_type="http_error",
                        error_message=f"HTTP {response.status if response else 'unknown'}",
                        antibot_detected=antibot_detected,
                    )

                raw_content = await page.content()
                content_hash = xxhash.xxh64(raw_content.encode()).hexdigest()
                content_size = len(raw_content.encode())

                # extraction_schema 기반 추출
                data = {}
                items_extracted = 0
                if task.extraction_schema:
                    from bs4 import BeautifulSoup
                    soup = BeautifulSoup(raw_content, "lxml")
                    for field, selector in task.extraction_schema.items():
                        try:
                            element = soup.select_one(selector)
                            if element:
                                data[field] = element.get_text(strip=True)
                                items_extracted += 1
                        except Exception as e:
                            logger.debug("selector_failed", field=field, error=str(e))

                await browser.close()
                duration_ms = int((time.monotonic() - start_time) * 1000)

                return ScrapeResult(
                    url_id=task.url_id,
                    url=task.url,
                    success=True,
                    pipeline_name=self.name,
                    pipeline_sequence=self.priority,
                    pipelines_attempted=pipelines_attempted,
                    duration_ms=duration_ms,
                    status_code=response.status if response else 200,
                    data=data,
                    raw_content=raw_content,
                    content_hash=content_hash,
                    content_size_bytes=content_size,
                    items_extracted=items_extracted,
                    antibot_detected=antibot_detected,
                    method_details={"browser": "chromium", "headless": True, "stealth": True},
                )

        except Exception as e:
            duration_ms = int((time.monotonic() - start_time) * 1000)
            logger.error("stealth_pipeline_error", url=task.url, error=str(e))
            return ScrapeResult(
                url_id=task.url_id,
                url=task.url,
                success=False,
                pipeline_name=self.name,
                pipeline_sequence=self.priority,
                pipelines_attempted=pipelines_attempted,
                duration_ms=duration_ms,
                error_type="browser_error",
                error_message=str(e),
            )

    async def health_check(self, url: str) -> bool:
        """Playwright 사용 가능 여부를 확인합니다."""
        try:
            from playwright.async_api import async_playwright  # noqa: F401
            return True
        except ImportError:
            return False
