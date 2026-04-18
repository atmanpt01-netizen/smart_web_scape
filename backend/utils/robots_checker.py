from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import httpx
import structlog

logger = structlog.get_logger(__name__)

_BOT_USER_AGENT = "SmartWebScraper/1.0 (+https://github.com/smart-web-scraper)"


async def check_robots_txt(url: str, user_agent: str = _BOT_USER_AGENT) -> bool:
    """
    robots.txt를 확인하여 해당 URL 수집 허용 여부를 반환합니다.

    Returns:
        True: 수집 허용 또는 robots.txt 없음
        False: 수집 차단
    """
    try:
        parsed = urlparse(url)
        robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                robots_url,
                headers={"User-Agent": _BOT_USER_AGENT},
                follow_redirects=True,
            )

        if response.status_code == 404:
            return True  # robots.txt 없으면 허용

        if response.status_code != 200:
            logger.warning("robots_txt_fetch_failed", url=robots_url, status=response.status_code)
            return True  # 접근 불가 시 허용으로 처리 (안전한 기본값)

        rp = RobotFileParser()
        rp.set_url(robots_url)
        rp.parse(response.text.splitlines())

        allowed = rp.can_fetch(user_agent, url)
        if not allowed:
            logger.info("robots_txt_disallowed", url=url)
        return allowed

    except Exception as e:
        logger.warning("robots_txt_check_error", url=url, error=str(e))
        return True  # 예외 시 허용으로 처리
