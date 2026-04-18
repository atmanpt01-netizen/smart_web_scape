"""프록시 풀 관리자."""
import random
from collections import defaultdict
from dataclasses import dataclass, field

import structlog

logger = structlog.get_logger(__name__)


@dataclass
class ProxyInfo:
    url: str
    failure_count: int = 0
    is_blacklisted: bool = False


class ProxyPool:
    """주거용 프록시 풀 관리."""

    def __init__(self, proxy_urls: list[str] | None = None) -> None:
        self._proxies: list[ProxyInfo] = [ProxyInfo(url=p) for p in (proxy_urls or [])]
        self._blacklist_threshold = 5

    def add_proxy(self, proxy_url: str) -> None:
        """프록시를 풀에 추가합니다."""
        self._proxies.append(ProxyInfo(url=proxy_url))

    async def get_proxy(self) -> str | None:
        """사용 가능한 프록시를 랜덤으로 반환합니다."""
        available = [p for p in self._proxies if not p.is_blacklisted]
        if not available:
            logger.warning("no_proxies_available")
            return None
        return random.choice(available).url

    async def report_failure(self, proxy_url: str) -> None:
        """실패한 프록시를 기록하고 임계값 초과 시 블랙리스트에 추가합니다."""
        for proxy in self._proxies:
            if proxy.url == proxy_url:
                proxy.failure_count += 1
                if proxy.failure_count >= self._blacklist_threshold:
                    proxy.is_blacklisted = True
                    logger.warning("proxy_blacklisted", proxy=self._mask_proxy(proxy_url))
                break

    async def report_success(self, proxy_url: str) -> None:
        """성공한 프록시의 실패 횟수를 리셋합니다."""
        for proxy in self._proxies:
            if proxy.url == proxy_url:
                proxy.failure_count = 0
                break

    @staticmethod
    def _mask_proxy(proxy_url: str) -> str:
        """프록시 IP 마지막 옥텟을 마스킹합니다."""
        parts = proxy_url.split(".")
        if len(parts) >= 4:
            parts[-1] = parts[-1].split(":")[0][:3] + "xxx" + (
                ":" + parts[-1].split(":")[1] if ":" in parts[-1] else ""
            )
        return ".".join(parts)

    @property
    def available_count(self) -> int:
        return len([p for p in self._proxies if not p.is_blacklisted])

    @property
    def total_count(self) -> int:
        return len(self._proxies)


# 싱글턴
_proxy_pool: ProxyPool | None = None


def get_proxy_pool() -> ProxyPool:
    global _proxy_pool
    if _proxy_pool is None:
        from backend.config import get_settings
        settings = get_settings()
        _proxy_pool = ProxyPool()
        # 외부 프록시 풀 URL에서 로드 (설정 시)
        if settings.proxy_pool_url:
            logger.info("proxy_pool_configured", url=settings.proxy_pool_url)
    return _proxy_pool
