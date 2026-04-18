"""Self-Healing Engine

5단계 자동 복구 전략을 적용합니다.
L1: 셀렉터 수리 → L2: 구조 변경 감지 → L3: 안티봇 대응 → L4: CAPTCHA → L5: 대안 탐색
"""
from dataclasses import dataclass

import structlog

from backend.api.schemas import ScrapeResult, ScrapeTask

logger = structlog.get_logger(__name__)


@dataclass
class ScrapeError:
    type: str
    message: str
    status_code: int | None = None


@dataclass
class HealingResult:
    success: bool
    healing_type: str
    result: ScrapeResult | None = None
    message: str = ""


class SelfHealingEngine:
    """에러 유형별 자동 복구 전략을 실행합니다."""

    async def heal(self, task: ScrapeTask, error: ScrapeError) -> HealingResult:
        """에러 유형에 맞는 복구 전략을 선택하고 실행합니다."""
        logger.info("healing_started", url=task.url, error_type=error.type)

        match error.type:
            case "selector_not_found" | "extraction_failed":
                return await self._heal_selector(task, error)
            case "structure_changed" | "content_changed":
                return await self._heal_structure(task)
            case "blocked" | "forbidden" | "challenge" | "rate_limited":
                return await self._heal_antibot(task, error)
            case "captcha":
                return await self._heal_captcha(task)
            case _:
                return await self._find_alternative(task, error)

    async def _heal_selector(self, task: ScrapeTask, error: ScrapeError) -> HealingResult:
        """L1: CSS 셀렉터 자동 수리."""
        from backend.healing.selector_repair import SelectorRepair
        repairer = SelectorRepair()
        return await repairer.repair(task, error)

    async def _heal_structure(self, task: ScrapeTask) -> HealingResult:
        """L2: LLM 기반 구조 변경 감지 및 새 셀렉터 생성."""
        from backend.healing.structure_detector import StructureDetector
        detector = StructureDetector()
        return await detector.detect_and_adapt(task)

    async def _heal_antibot(self, task: ScrapeTask, error: ScrapeError) -> HealingResult:
        """L3: 안티봇 탐지 대응 (핑거프린트 순환, 프록시 교체, 딜레이 증가)."""
        from backend.healing.fingerprint_rotator import FingerprintRotator
        rotator = FingerprintRotator()
        return await rotator.rotate_and_retry(task, error)

    async def _heal_captcha(self, task: ScrapeTask) -> HealingResult:
        """L4: CAPTCHA 솔버 (Phase 5에서 구현)."""
        logger.warning("captcha_healing_not_implemented", url=task.url)
        return HealingResult(
            success=False,
            healing_type="captcha",
            message="CAPTCHA 솔버가 아직 구현되지 않았습니다. (Phase 5 예정)",
        )

    async def _find_alternative(self, task: ScrapeTask, error: ScrapeError) -> HealingResult:
        """L5: 대안 진입점 탐색 (RSS, 캐시 등)."""
        logger.warning("alternative_search_not_implemented", url=task.url, error=error.type)
        return HealingResult(
            success=False,
            healing_type="alternative",
            message="대안 진입점 탐색이 구현되지 않았습니다. 관리자 알림이 필요합니다.",
        )
