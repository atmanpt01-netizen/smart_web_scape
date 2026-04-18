"""Pipeline 4: AI-Powered Extraction

Crawl4AI + Ollama(로컬 LLM)를 사용해 구조 변경에도 강건하게 데이터를 추출합니다.
페이지를 Markdown으로 변환한 후 LLM에 전달합니다.
"""
import asyncio
import time
from typing import Any

import structlog
import xxhash

from backend.api.schemas import ScrapeResult, ScrapeTask
from backend.config import get_settings
from backend.pipelines.base import BasePipeline

logger = structlog.get_logger(__name__)
settings = get_settings()

# LLM 모델 우선순위 (VRAM 요구량 순)
LLM_MODELS = ["llama3.2:8b", "mistral:7b", "llama3.2:3b"]


class AiPipeline(BasePipeline):
    """Pipeline 4: Crawl4AI + Ollama 기반 AI 추출."""

    name = "ai"
    priority = 4
    estimated_cost = 0.8
    avg_response_time = 20.0

    # Circuit Breaker 상태
    _failure_count: int = 0
    _is_open: bool = False
    _last_failure_time: float = 0.0
    FAILURE_THRESHOLD = 5
    RECOVERY_TIMEOUT = 300  # 5분

    async def execute(self, task: ScrapeTask) -> ScrapeResult:
        start_time = time.monotonic()
        pipelines_attempted = ["ai"]

        # Circuit Breaker 확인
        if self._is_circuit_open():
            duration_ms = int((time.monotonic() - start_time) * 1000)
            return ScrapeResult(
                url_id=task.url_id,
                url=task.url,
                success=False,
                pipeline_name=self.name,
                pipeline_sequence=self.priority,
                pipelines_attempted=pipelines_attempted,
                duration_ms=duration_ms,
                error_type="circuit_breaker_open",
                error_message="AI 파이프라인 회로 차단기 활성화 (과도한 실패)",
            )

        try:
            result = await self._extract_with_ai(task)
            if result.success:
                self._reset_circuit()
            else:
                self._record_failure()

            duration_ms = int((time.monotonic() - start_time) * 1000)
            result.duration_ms = duration_ms
            return result

        except Exception as e:
            self._record_failure()
            duration_ms = int((time.monotonic() - start_time) * 1000)
            logger.error("ai_pipeline_error", url=task.url, error=str(e))
            return ScrapeResult(
                url_id=task.url_id,
                url=task.url,
                success=False,
                pipeline_name=self.name,
                pipeline_sequence=self.priority,
                pipelines_attempted=pipelines_attempted,
                duration_ms=duration_ms,
                error_type="ai_extraction_error",
                error_message=str(e),
            )

    async def _extract_with_ai(self, task: ScrapeTask) -> ScrapeResult:
        """Crawl4AI로 페이지를 크롤링하고 Ollama LLM으로 데이터를 추출합니다."""
        try:
            from crawl4ai import AsyncWebCrawler

            async with AsyncWebCrawler(verbose=False) as crawler:
                crawl_result = await crawler.arun(url=task.url)

            if not crawl_result.success:
                return ScrapeResult(
                    url_id=task.url_id,
                    url=task.url,
                    success=False,
                    pipeline_name=self.name,
                    pipeline_sequence=self.priority,
                    pipelines_attempted=["ai"],
                    duration_ms=0,
                    error_type="crawl_failed",
                    error_message="Crawl4AI 크롤링 실패",
                )

            markdown_content = crawl_result.markdown or ""
            raw_content = crawl_result.html or ""
            content_hash = xxhash.xxh64(raw_content.encode()).hexdigest()

            # LLM으로 구조화 추출
            data = {}
            items_extracted = 0
            if task.extraction_schema and markdown_content:
                data, items_extracted = await self._llm_extract(markdown_content, task.extraction_schema)

            return ScrapeResult(
                url_id=task.url_id,
                url=task.url,
                success=True,
                pipeline_name=self.name,
                pipeline_sequence=self.priority,
                pipelines_attempted=["ai"],
                duration_ms=0,
                status_code=200,
                data=data,
                raw_content=raw_content,
                content_hash=content_hash,
                content_size_bytes=len(raw_content.encode()),
                items_extracted=items_extracted,
                method_details={"llm_model": settings.ollama_model, "via_crawl4ai": True},
            )

        except ImportError:
            return ScrapeResult(
                url_id=task.url_id,
                url=task.url,
                success=False,
                pipeline_name=self.name,
                pipeline_sequence=self.priority,
                pipelines_attempted=["ai"],
                duration_ms=0,
                error_type="dependency_missing",
                error_message="crawl4ai가 설치되지 않았습니다.",
            )

    async def _llm_extract(
        self, markdown: str, schema: dict[str, str]
    ) -> tuple[dict[str, Any], int]:
        """Ollama LLM을 사용해 Markdown에서 구조화된 데이터를 추출합니다."""
        try:
            import ollama

            schema_desc = "\n".join(f"- {k}: {v}" for k, v in schema.items())
            prompt = f"""다음 웹페이지 콘텐츠(Markdown 형식)에서 아래 필드들을 추출해주세요.
각 필드에 해당하는 내용이 없으면 null을 반환하세요.
반드시 JSON 형식으로만 응답해주세요.

추출할 필드:
{schema_desc}

콘텐츠:
{markdown[:3000]}

JSON 응답:"""

            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: ollama.generate(
                    model=settings.ollama_model,
                    prompt=prompt,
                    options={"temperature": 0.1, "top_p": 0.9},
                ),
            )

            import json
            response_text = response["response"].strip()
            # JSON 블록 추출
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0].strip()

            data = json.loads(response_text)
            items_extracted = sum(1 for v in data.values() if v is not None)
            return data, items_extracted

        except Exception as e:
            logger.warning("llm_extraction_failed", error=str(e))
            return {}, 0

    def _is_circuit_open(self) -> bool:
        if not self._is_open:
            return False
        # RECOVERY_TIMEOUT 후 Half-Open 상태로 전환
        if time.monotonic() - self._last_failure_time > self.RECOVERY_TIMEOUT:
            self._is_open = False
            self._failure_count = 0
            return False
        return True

    def _record_failure(self) -> None:
        self._failure_count += 1
        self._last_failure_time = time.monotonic()
        if self._failure_count >= self.FAILURE_THRESHOLD:
            self._is_open = True
            logger.warning("ai_pipeline_circuit_opened", failures=self._failure_count)

    def _reset_circuit(self) -> None:
        self._failure_count = 0
        self._is_open = False

    async def health_check(self, url: str) -> bool:
        """Ollama 및 Crawl4AI 사용 가능 여부를 확인합니다."""
        if self._is_circuit_open():
            return False
        try:
            import httpx
            async with httpx.AsyncClient(timeout=3.0) as client:
                response = await client.get(f"{settings.ollama_url}/api/tags")
            return response.status_code == 200
        except Exception:
            return False
