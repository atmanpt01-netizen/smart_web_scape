"""L2 Self-Healing: LLM 기반 페이지 구조 변경 감지 및 적응."""
import structlog
import xxhash

from backend.api.schemas import ScrapeTask
from backend.healing.engine import HealingResult

logger = structlog.get_logger(__name__)


class StructureDetector:
    """페이지 구조 해시 비교 및 LLM 기반 새 셀렉터 생성."""

    async def detect_and_adapt(self, task: ScrapeTask) -> HealingResult:
        """구조 변경을 감지하고 새 셀렉터를 생성합니다."""
        # 페이지 재수집
        raw_content = await self._fetch_page(task.url)
        if not raw_content:
            return HealingResult(
                success=False,
                healing_type="structure_detection",
                message="페이지 재수집 실패",
            )

        new_hash = xxhash.xxh64(raw_content.encode()).hexdigest()
        logger.info("structure_hash_computed", url=task.url, hash=new_hash)

        if not task.extraction_schema:
            return HealingResult(
                success=False,
                healing_type="structure_detection",
                message="추출 스키마가 없어 구조 적응 불가",
            )

        # Crawl4AI로 Markdown 변환 후 LLM 분석
        markdown_content = await self._page_to_markdown(raw_content)
        new_selectors = await self._llm_analyze_structure(markdown_content, task.extraction_schema)

        if not new_selectors:
            return HealingResult(
                success=False,
                healing_type="structure_detection",
                message="LLM이 새 셀렉터를 도출하지 못했습니다.",
            )

        # 새 셀렉터로 데이터 추출
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(raw_content, "lxml")
        data = {}
        for field, selector in new_selectors.items():
            try:
                element = soup.select_one(selector)
                if element:
                    data[field] = element.get_text(strip=True)
            except Exception:
                pass

        from backend.api.schemas import ScrapeResult
        result = ScrapeResult(
            url_id=task.url_id,
            url=task.url,
            success=len(data) > 0,
            pipeline_name="http",
            pipeline_sequence=2,
            pipelines_attempted=["http"],
            duration_ms=0,
            data=data,
            content_hash=new_hash,
            items_extracted=len(data),
            healing_applied=True,
            healing_type="structure_detection",
            method_details={"new_selectors": new_selectors},
        )

        return HealingResult(
            success=len(data) > 0,
            healing_type="structure_detection",
            result=result,
            message=f"구조 적응 완료: {len(data)}개 필드 추출",
        )

    async def _page_to_markdown(self, html: str) -> str:
        """HTML을 Markdown으로 변환합니다."""
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, "lxml")
            # 스크립트/스타일 제거
            for tag in soup(["script", "style", "nav", "footer", "header"]):
                tag.decompose()
            return soup.get_text(separator="\n", strip=True)[:4000]
        except Exception:
            return html[:4000]

    async def _llm_analyze_structure(
        self, content: str, schema: dict[str, str]
    ) -> dict[str, str] | None:
        """LLM으로 페이지 구조를 분석하고 새 CSS 셀렉터를 반환합니다."""
        try:
            import asyncio
            import json
            import ollama
            from backend.config import get_settings

            settings = get_settings()
            fields = ", ".join(schema.keys())

            prompt = f"""다음 웹페이지 텍스트에서 아래 필드들을 추출할 CSS 셀렉터를 JSON 형식으로 제안해주세요.
필드: {fields}

페이지 내용:
{content}

JSON 형식으로만 응답 (예: {{"title": "h1.article-title", "date": ".pub-date"}}):"""

            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: ollama.generate(
                    model=settings.ollama_model,
                    prompt=prompt,
                    options={"temperature": 0.1},
                ),
            )

            response_text = response["response"].strip()
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0].strip()

            return json.loads(response_text)
        except Exception as e:
            logger.warning("llm_structure_analysis_failed", error=str(e))
            return None

    async def _fetch_page(self, url: str) -> str | None:
        try:
            import httpx
            async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
                response = await client.get(url)
            if response.status_code == 200:
                return response.text
        except Exception:
            pass
        return None
