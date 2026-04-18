import asyncio
import time
from collections import defaultdict
from urllib.parse import urlparse

import structlog

logger = structlog.get_logger(__name__)

# 도메인 카테고리별 Rate Limit 설정
DOMAIN_RATE_LIMITS: dict[str, dict] = {
    "news": {"max_concurrent": 3, "delay_ms": 1000},
    "portal": {"max_concurrent": 2, "delay_ms": 3000},
    "ecommerce": {"max_concurrent": 2, "delay_ms": 2000},
    "enterprise": {"max_concurrent": 5, "delay_ms": 1000},
    "government": {"max_concurrent": 3, "delay_ms": 1000},
    "finance": {"max_concurrent": 2, "delay_ms": 2000},
    "sns": {"max_concurrent": 1, "delay_ms": 3000},
    "default": {"max_concurrent": 3, "delay_ms": 1000},
}


class DomainRateLimiter:
    """도메인별 동시 요청 수 및 요청 간격을 제한합니다."""

    def __init__(self) -> None:
        self._last_request: dict[str, float] = defaultdict(float)
        self._semaphores: dict[str, asyncio.Semaphore] = {}
        self._locks: dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)

    def _get_config(self, category: str) -> dict:
        return DOMAIN_RATE_LIMITS.get(category, DOMAIN_RATE_LIMITS["default"])

    def _get_semaphore(self, domain: str, category: str) -> asyncio.Semaphore:
        if domain not in self._semaphores:
            config = self._get_config(category)
            self._semaphores[domain] = asyncio.Semaphore(config["max_concurrent"])
        return self._semaphores[domain]

    async def acquire(self, url: str, category: str = "default") -> None:
        """요청 전 Rate Limit을 적용합니다."""
        parsed = urlparse(url)
        domain = parsed.netloc.lower()

        config = self._get_config(category)
        delay_sec = config["delay_ms"] / 1000.0

        semaphore = self._get_semaphore(domain, category)
        await semaphore.acquire()

        # 마지막 요청으로부터 최소 딜레이 적용
        async with self._locks[domain]:
            now = time.monotonic()
            elapsed = now - self._last_request[domain]
            if elapsed < delay_sec:
                wait_time = delay_sec - elapsed
                logger.debug("rate_limit_wait", domain=domain, wait_ms=int(wait_time * 1000))
                await asyncio.sleep(wait_time)
            self._last_request[domain] = time.monotonic()

    def release(self, url: str, category: str = "default") -> None:
        """요청 완료 후 Semaphore를 해제합니다."""
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        semaphore = self._get_semaphore(domain, category)
        semaphore.release()


# 전역 싱글턴
_rate_limiter: DomainRateLimiter | None = None


def get_rate_limiter() -> DomainRateLimiter:
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = DomainRateLimiter()
    return _rate_limiter
