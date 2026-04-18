"""L3 Self-Healing: 브라우저/TLS 핑거프린트 순환."""
import asyncio
import random

import structlog

from backend.api.schemas import ScrapeTask
from backend.healing.engine import HealingResult, ScrapeError
from backend.utils.user_agents import get_random_user_agent

logger = structlog.get_logger(__name__)

# TLS 핑거프린트 프로파일
TLS_PROFILES = ["chrome131", "chrome130", "firefox133", "safari17_0", "chrome99"]

# 안티봇 유형별 대응 전략
ANTIBOT_STRATEGIES = {
    "cloudflare": {"delay_ms": 5000, "rotate_ip": True, "use_residential": True},
    "datadome": {"delay_ms": 3000, "rotate_ua": True, "rotate_tls": True},
    "akamai": {"delay_ms": 4000, "rotate_ip": True, "rotate_tls": True},
    "default": {"delay_ms": 2000, "rotate_ua": True, "rotate_tls": True},
}


class FingerprintRotator:
    """User-Agent, TLS 핑거프린트, 딜레이를 순환하여 안티봇을 우회합니다."""

    async def rotate_and_retry(self, task: ScrapeTask, error: ScrapeError) -> HealingResult:
        """핑거프린트를 순환하고 재시도합니다."""
        antibot_type = error.message.lower() if error.message else "default"
        strategy = self._detect_strategy(antibot_type)

        # 딜레이 적용
        delay_sec = strategy["delay_ms"] / 1000.0
        logger.info(
            "fingerprint_rotation_started",
            url=task.url,
            delay_sec=delay_sec,
            strategy=antibot_type,
        )
        await asyncio.sleep(delay_sec)

        # TLS 핑거프린트 순환하여 재시도
        tls_profile = random.choice(TLS_PROFILES)
        new_ua = get_random_user_agent()

        result = await self._retry_with_cffi(task, tls_profile, new_ua)
        if result.success:
            result.healing_applied = True
            result.healing_type = "fingerprint_rotation"
            return HealingResult(
                success=True,
                healing_type="fingerprint_rotation",
                result=result,
                message=f"핑거프린트 순환 성공: TLS={tls_profile}",
            )

        # cffi 실패 시 Stealth 브라우저로 재시도
        from backend.pipelines.stealth_pipeline import StealthPipeline
        stealth = StealthPipeline()
        result = await stealth.execute(task)
        if result.success:
            result.healing_applied = True
            result.healing_type = "fingerprint_rotation"
            return HealingResult(
                success=True,
                healing_type="fingerprint_rotation",
                result=result,
                message="Stealth 브라우저 재시도 성공",
            )

        return HealingResult(
            success=False,
            healing_type="fingerprint_rotation",
            message="핑거프린트 순환 후에도 실패 — Proxy 파이프라인 필요",
        )

    def _detect_strategy(self, antibot_hint: str) -> dict:
        """안티봇 유형에 맞는 전략을 반환합니다."""
        for antibot_name, strategy in ANTIBOT_STRATEGIES.items():
            if antibot_name in antibot_hint:
                return strategy
        return ANTIBOT_STRATEGIES["default"]

    async def _retry_with_cffi(self, task: ScrapeTask, tls_profile: str, user_agent: str) -> any:
        """curl_cffi로 TLS 핑거프린트를 변경하여 재시도합니다."""
        from backend.api.schemas import ScrapeResult
        import time

        start_time = time.monotonic()
        try:
            from curl_cffi.requests import AsyncSession
            import xxhash

            async with AsyncSession() as session:
                response = await session.get(
                    task.url,
                    headers={"User-Agent": user_agent, "Accept-Language": "ko-KR,ko;q=0.9"},
                    timeout=30,
                    impersonate=tls_profile,
                )

            if response.status_code not in range(200, 300):
                return ScrapeResult(
                    url_id=task.url_id, url=task.url, success=False,
                    pipeline_name="http", pipeline_sequence=2,
                    pipelines_attempted=["http_cffi"], duration_ms=0,
                    status_code=response.status_code,
                    error_type="http_error",
                )

            raw = response.text
            content_hash = xxhash.xxh64(raw.encode()).hexdigest()
            data = {}
            if task.extraction_schema:
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(raw, "lxml")
                for field, selector in task.extraction_schema.items():
                    try:
                        el = soup.select_one(selector)
                        if el:
                            data[field] = el.get_text(strip=True)
                    except Exception:
                        pass

            duration_ms = int((time.monotonic() - start_time) * 1000)
            return ScrapeResult(
                url_id=task.url_id, url=task.url, success=True,
                pipeline_name="http", pipeline_sequence=2,
                pipelines_attempted=["http_cffi"], duration_ms=duration_ms,
                status_code=response.status_code, data=data,
                content_hash=content_hash, raw_content=raw,
                items_extracted=len(data),
                method_details={"tls_profile": tls_profile, "user_agent": user_agent},
            )
        except Exception as e:
            duration_ms = int((time.monotonic() - start_time) * 1000)
            return ScrapeResult(
                url_id=task.url_id, url=task.url, success=False,
                pipeline_name="http", pipeline_sequence=2,
                pipelines_attempted=["http_cffi"], duration_ms=duration_ms,
                error_type="cffi_error", error_message=str(e),
            )
