"""Pipeline 5: Proxy + Full Browser

Playwright + 주거용 프록시 + TLS 핑거프린트 순환.
가장 강력하지만 가장 비용이 높은 파이프라인.
"""
import time

import structlog
import xxhash

from backend.api.schemas import ScrapeResult, ScrapeTask
from backend.pipelines.base import BasePipeline
from backend.utils.proxy_pool import get_proxy_pool
from backend.utils.user_agents import get_random_user_agent

logger = structlog.get_logger(__name__)

# TLS 핑거프린트 프로파일 (curl_cffi impersonate 옵션)
TLS_PROFILES = ["chrome131", "chrome130", "firefox133", "safari17_0"]


class ProxyPipeline(BasePipeline):
    """Pipeline 5: Proxy + Playwright Full Browser."""

    name = "proxy"
    priority = 5
    estimated_cost = 1.0
    avg_response_time = 15.0

    async def execute(self, task: ScrapeTask) -> ScrapeResult:
        start_time = time.monotonic()
        pipelines_attempted = ["proxy"]
        proxy_pool = get_proxy_pool()

        proxy_url = await proxy_pool.get_proxy()
        if not proxy_url:
            duration_ms = int((time.monotonic() - start_time) * 1000)
            return ScrapeResult(
                url_id=task.url_id,
                url=task.url,
                success=False,
                pipeline_name=self.name,
                pipeline_sequence=self.priority,
                pipelines_attempted=pipelines_attempted,
                duration_ms=duration_ms,
                error_type="no_proxy_available",
                error_message="사용 가능한 프록시가 없습니다.",
            )

        try:
            from playwright.async_api import async_playwright

            async with async_playwright() as p:
                browser = await p.chromium.launch(
                    headless=True,
                    proxy={"server": proxy_url},
                    args=[
                        "--no-sandbox",
                        "--disable-setuid-sandbox",
                        "--disable-blink-features=AutomationControlled",
                    ],
                )

                context = await browser.new_context(
                    user_agent=get_random_user_agent("chrome"),
                    locale="ko-KR",
                    timezone_id="Asia/Seoul",
                    viewport={"width": 1920, "height": 1080},
                    extra_http_headers={
                        "Accept-Language": "ko-KR,ko;q=0.9",
                        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    },
                )

                await context.add_init_script("""
                    Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
                """)

                page = await context.new_page()
                response = await page.goto(task.url, wait_until="networkidle", timeout=45000)

                if response and response.status not in range(200, 300):
                    await proxy_pool.report_failure(proxy_url)
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
                    )

                raw_content = await page.content()
                content_hash = xxhash.xxh64(raw_content.encode()).hexdigest()

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
                        except Exception:
                            pass

                await browser.close()
                await proxy_pool.report_success(proxy_url)

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
                    content_size_bytes=len(raw_content.encode()),
                    items_extracted=items_extracted,
                    proxy_used=proxy_pool._mask_proxy(proxy_url),
                    method_details={"browser": "chromium", "proxy": True},
                )

        except Exception as e:
            await proxy_pool.report_failure(proxy_url)
            duration_ms = int((time.monotonic() - start_time) * 1000)
            logger.error("proxy_pipeline_error", url=task.url, error=str(e))
            return ScrapeResult(
                url_id=task.url_id,
                url=task.url,
                success=False,
                pipeline_name=self.name,
                pipeline_sequence=self.priority,
                pipelines_attempted=pipelines_attempted,
                duration_ms=duration_ms,
                error_type="proxy_error",
                error_message=str(e),
            )

    async def health_check(self, url: str) -> bool:
        """프록시 풀 및 Playwright 사용 가능 여부 확인."""
        pool = get_proxy_pool()
        if pool.total_count > 0 and pool.available_count == 0:
            return False
        try:
            from playwright.async_api import async_playwright  # noqa: F401
            return True
        except ImportError:
            return False
