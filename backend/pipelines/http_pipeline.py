import time
import uuid
from typing import Any
from urllib.parse import urlparse

import httpx
import structlog
import xxhash
from bs4 import BeautifulSoup
from tenacity import retry, stop_after_attempt, wait_exponential

from backend.api.schemas import ScrapeResult, ScrapeTask
from backend.pipelines.base import BasePipeline

logger = structlog.get_logger(__name__)

_DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept-Encoding": "gzip, deflate, br",
}


class HttpPipeline(BasePipeline):
    """Pipeline 2: HTTP + Smart Parser

    httpx(HTTP/2) + BeautifulSoup4 기반 수집.
    안티봇 감지 시 curl_cffi TLS 핑거프린트 스푸핑으로 폴백.
    """

    name = "http"
    priority = 2
    estimated_cost = 0.1
    avg_response_time = 3.0

    async def execute(self, task: ScrapeTask) -> ScrapeResult:
        start_time = time.monotonic()
        pipelines_attempted = ["http"]

        await self.pre_execute(task)

        try:
            result = await self._fetch_with_httpx(task)
            if result["success"]:
                duration_ms = int((time.monotonic() - start_time) * 1000)
                return self._build_result(task, result, duration_ms, pipelines_attempted)

            # httpx 실패 시 curl_cffi 폴백
            pipelines_attempted.append("http_cffi")
            result = await self._fetch_with_curl_cffi(task)
            duration_ms = int((time.monotonic() - start_time) * 1000)
            return self._build_result(task, result, duration_ms, pipelines_attempted)

        except Exception as e:
            duration_ms = int((time.monotonic() - start_time) * 1000)
            logger.error("http_pipeline_error", url=task.url, error=str(e))
            return ScrapeResult(
                url_id=task.url_id,
                url=task.url,
                success=False,
                pipeline_name=self.name,
                pipeline_sequence=self.priority,
                pipelines_attempted=pipelines_attempted,
                duration_ms=duration_ms,
                error_type="exception",
                error_message=str(e),
            )

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10))
    async def _fetch_with_httpx(self, task: ScrapeTask) -> dict[str, Any]:
        async with httpx.AsyncClient(
            headers=_DEFAULT_HEADERS,
            timeout=httpx.Timeout(30.0),
            follow_redirects=True,
            http2=True,
        ) as client:
            response = await client.get(task.url)

        return self._process_response(response, task)

    async def _fetch_with_curl_cffi(self, task: ScrapeTask) -> dict[str, Any]:
        try:
            from curl_cffi.requests import AsyncSession

            async with AsyncSession() as session:
                response = await session.get(
                    task.url,
                    headers=_DEFAULT_HEADERS,
                    timeout=30,
                    impersonate="chrome131",
                )

            return self._process_response(response, task)
        except ImportError:
            logger.warning("curl_cffi_not_available")
            return {"success": False, "error_type": "dependency_missing", "error_message": "curl_cffi not installed"}

    def _process_response(self, response: Any, task: ScrapeTask) -> dict[str, Any]:
        status_code = response.status_code

        # 안티봇 감지
        antibot_detected = None
        if status_code in (403, 429, 503):
            antibot_detected = f"http_{status_code}"

        if status_code not in range(200, 300):
            return {
                "success": False,
                "status_code": status_code,
                "error_type": "http_error",
                "error_message": f"HTTP {status_code}",
                "antibot_detected": antibot_detected,
            }

        raw_content = response.text
        content_hash = xxhash.xxh64(raw_content.encode()).hexdigest()
        content_size = len(raw_content.encode())

        # extraction_schema 기반 데이터 추출
        data = {}
        items_extracted = 0
        if task.extraction_schema:
            soup = BeautifulSoup(raw_content, "lxml")
            for field, selector in task.extraction_schema.items():
                try:
                    element = soup.select_one(selector)
                    if element:
                        data[field] = element.get_text(strip=True)
                        items_extracted += 1
                except Exception as e:
                    logger.debug("selector_extraction_failed", field=field, selector=selector, error=str(e))

        return {
            "success": True,
            "status_code": status_code,
            "raw_content": raw_content,
            "content_hash": content_hash,
            "content_size_bytes": content_size,
            "data": data,
            "items_extracted": items_extracted,
            "antibot_detected": antibot_detected,
        }

    def _build_result(
        self,
        task: ScrapeTask,
        fetch_result: dict[str, Any],
        duration_ms: int,
        pipelines_attempted: list[str],
    ) -> ScrapeResult:
        return ScrapeResult(
            url_id=task.url_id,
            url=task.url,
            success=fetch_result.get("success", False),
            pipeline_name=self.name,
            pipeline_sequence=self.priority,
            pipelines_attempted=pipelines_attempted,
            duration_ms=duration_ms,
            status_code=fetch_result.get("status_code"),
            error_type=fetch_result.get("error_type"),
            error_message=fetch_result.get("error_message"),
            data=fetch_result.get("data"),
            raw_content=fetch_result.get("raw_content"),
            content_hash=fetch_result.get("content_hash"),
            content_size_bytes=fetch_result.get("content_size_bytes"),
            items_extracted=fetch_result.get("items_extracted"),
            antibot_detected=fetch_result.get("antibot_detected"),
            method_details={"pipeline": "httpx", "http2": True},
        )

    async def health_check(self, url: str) -> bool:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.head(url, follow_redirects=True)
                return response.status_code < 500
        except Exception:
            return False
