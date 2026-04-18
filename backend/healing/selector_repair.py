"""L1 Self-Healing: CSS 셀렉터 자동 수리."""
import structlog
from bs4 import BeautifulSoup

from backend.api.schemas import ScrapeTask
from backend.healing.engine import HealingResult, ScrapeError

logger = structlog.get_logger(__name__)


class SelectorRepair:
    """CSS 셀렉터 퍼지 매칭 및 LLM 기반 재생성."""

    async def repair(self, task: ScrapeTask, error: ScrapeError) -> HealingResult:
        """셀렉터 수리를 시도합니다."""
        if not task.extraction_schema:
            return HealingResult(success=False, healing_type="selector_repair", message="추출 스키마가 없습니다.")

        # 페이지 재수집 (기본 HTTP)
        raw_content = await self._fetch_page(task.url)
        if not raw_content:
            return HealingResult(success=False, healing_type="selector_repair", message="페이지 재수집 실패")

        soup = BeautifulSoup(raw_content, "lxml")
        repaired_schema = {}
        repair_count = 0

        for field, selector in task.extraction_schema.items():
            # 기존 셀렉터 시도
            if soup.select_one(selector):
                repaired_schema[field] = selector
                continue

            # 퍼지 매칭: 셀렉터 변형 시도
            candidates = self._generate_selector_candidates(selector)
            repaired = False
            for candidate in candidates:
                try:
                    if soup.select_one(candidate):
                        repaired_schema[field] = candidate
                        repair_count += 1
                        repaired = True
                        logger.info("selector_repaired", field=field, old=selector, new=candidate)
                        break
                except Exception:
                    continue

            if not repaired:
                # LLM 기반 셀렉터 생성 시도 (Ollama 사용)
                llm_selector = await self._llm_generate_selector(soup, field)
                if llm_selector and soup.select_one(llm_selector):
                    repaired_schema[field] = llm_selector
                    repair_count += 1
                    logger.info("selector_repaired_by_llm", field=field, new=llm_selector)
                else:
                    repaired_schema[field] = selector  # 원본 유지

        if repair_count > 0:
            # 수리된 스키마로 재수집
            data = {}
            for field, selector in repaired_schema.items():
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
                success=True,
                pipeline_name="http",
                pipeline_sequence=2,
                pipelines_attempted=["http"],
                duration_ms=0,
                data=data,
                items_extracted=len(data),
                healing_applied=True,
                healing_type="selector_repair",
                method_details={"repaired_selectors": repair_count},
            )
            return HealingResult(success=True, healing_type="selector_repair", result=result)

        return HealingResult(
            success=False,
            healing_type="selector_repair",
            message="셀렉터 수리 불가 — 구조가 크게 변경되었을 수 있습니다.",
        )

    def _generate_selector_candidates(self, original: str) -> list[str]:
        """원본 셀렉터의 변형 후보를 생성합니다."""
        candidates = []

        # 클래스 기반 셀렉터의 경우 부분 클래스 매칭
        if "." in original:
            parts = original.split(".")
            if len(parts) > 1:
                # 앞부분 태그만
                candidates.append(parts[0] if parts[0] else "*")
                # 마지막 클래스만
                candidates.append(f".{parts[-1]}")

        # ID 기반 셀렉터의 경우
        if "#" in original:
            candidates.append(original.split("#")[0] or "*")

        # aria-label, data-* 속성 시도
        candidates.extend([
            f"[data-id]",
            f"[role='main'] {original}",
            f"main {original}",
            f"article {original}",
        ])

        return candidates

    async def _llm_generate_selector(self, soup: BeautifulSoup, field_name: str) -> str | None:
        """LLM을 사용해 필드에 적합한 CSS 셀렉터를 생성합니다."""
        try:
            import asyncio
            import ollama
            from backend.config import get_settings

            settings = get_settings()
            # HTML 구조 일부 추출 (LLM에 전달)
            html_snippet = str(soup.body)[:2000] if soup.body else str(soup)[:2000]

            prompt = f"""다음 HTML에서 '{field_name}' 정보를 추출할 수 있는 CSS 셀렉터를 하나만 반환하세요.
셀렉터만 반환하고 설명은 하지 마세요.

HTML:
{html_snippet}

CSS 셀렉터:"""

            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: ollama.generate(
                    model=settings.ollama_model,
                    prompt=prompt,
                    options={"temperature": 0.1},
                ),
            )
            return response["response"].strip()
        except Exception as e:
            logger.debug("llm_selector_generation_failed", error=str(e))
            return None

    async def _fetch_page(self, url: str) -> str | None:
        """페이지를 기본 HTTP로 재수집합니다."""
        try:
            import httpx
            async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
                response = await client.get(url)
            if response.status_code == 200:
                return response.text
        except Exception:
            pass
        return None
