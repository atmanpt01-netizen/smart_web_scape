"""Pipeline 1: Official API Client

공식 API가 있는 경우 스크래핑 대신 API를 우선 사용합니다.
지원 API: 공공데이터포털, Naver Search, Kakao Search, DART, YouTube Data API
"""
import re
import time
from typing import Any
from urllib.parse import urlparse

import httpx
import structlog

from backend.api.schemas import ScrapeResult, ScrapeTask
from backend.config import get_settings
from backend.pipelines.base import BasePipeline

logger = structlog.get_logger(__name__)
settings = get_settings()


# URL 패턴 → API 매핑
API_MATCHERS: list[dict[str, Any]] = [
    {
        "pattern": r"data\.go\.kr",
        "name": "data_go_kr",
        "base_url": "https://api.data.go.kr/openapi",
    },
    {
        "pattern": r"search\.naver\.com|news\.naver\.com|blog\.naver\.com",
        "name": "naver_search",
        "base_url": "https://openapi.naver.com/v1/search",
    },
    {
        "pattern": r"search\.daum\.net|kakao\.com",
        "name": "kakao_search",
        "base_url": "https://dapi.kakao.com/v2/search",
    },
    {
        "pattern": r"dart\.fss\.or\.kr|kind\.krx\.co\.kr",
        "name": "dart",
        "base_url": "https://opendart.fss.or.kr/api",
    },
    {
        "pattern": r"youtube\.com|youtu\.be",
        "name": "youtube",
        "base_url": "https://www.googleapis.com/youtube/v3",
    },
]


class ApiPipeline(BasePipeline):
    """Pipeline 1: 공식 API 우선 사용 파이프라인."""

    name = "api"
    priority = 1
    estimated_cost = 0.0
    avg_response_time = 1.0

    async def execute(self, task: ScrapeTask) -> ScrapeResult:
        start_time = time.monotonic()

        api_info = self._detect_api(task.url)
        if not api_info:
            duration_ms = int((time.monotonic() - start_time) * 1000)
            return ScrapeResult(
                url_id=task.url_id,
                url=task.url,
                success=False,
                pipeline_name=self.name,
                pipeline_sequence=self.priority,
                pipelines_attempted=["api"],
                duration_ms=duration_ms,
                error_type="no_api_available",
                error_message="이 URL에 대한 공식 API가 없습니다.",
            )

        try:
            result = await self._call_api(api_info, task)
            duration_ms = int((time.monotonic() - start_time) * 1000)
            result.duration_ms = duration_ms
            return result
        except Exception as e:
            duration_ms = int((time.monotonic() - start_time) * 1000)
            logger.error("api_pipeline_error", url=task.url, api=api_info["name"], error=str(e))
            return ScrapeResult(
                url_id=task.url_id,
                url=task.url,
                success=False,
                pipeline_name=self.name,
                pipeline_sequence=self.priority,
                pipelines_attempted=["api"],
                duration_ms=duration_ms,
                error_type="api_error",
                error_message=str(e),
            )

    def _detect_api(self, url: str) -> dict[str, Any] | None:
        """URL에서 사용 가능한 API를 탐지합니다."""
        for matcher in API_MATCHERS:
            if re.search(matcher["pattern"], url, re.IGNORECASE):
                return matcher
        return None

    async def _call_api(self, api_info: dict[str, Any], task: ScrapeTask) -> ScrapeResult:
        """감지된 API를 호출합니다."""
        api_name = api_info["name"]

        if api_name == "naver_search":
            return await self._call_naver_api(task)
        elif api_name == "kakao_search":
            return await self._call_kakao_api(task)
        elif api_name == "dart":
            return await self._call_dart_api(task)
        elif api_name == "youtube":
            return await self._call_youtube_api(task)
        else:
            # 공공데이터포털 등 generic fallback
            return ScrapeResult(
                url_id=task.url_id,
                url=task.url,
                success=False,
                pipeline_name=self.name,
                pipeline_sequence=self.priority,
                pipelines_attempted=["api"],
                duration_ms=0,
                error_type="api_not_configured",
                error_message=f"{api_name} API 키가 설정되지 않았습니다.",
            )

    async def _call_naver_api(self, task: ScrapeTask) -> ScrapeResult:
        if not settings.naver_client_id or not settings.naver_client_secret:
            raise ValueError("Naver API 인증 정보가 설정되지 않았습니다.")

        parsed = urlparse(task.url)
        query = parsed.path.split("/")[-1] or parsed.hostname or ""

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                "https://openapi.naver.com/v1/search/news.json",
                params={"query": query, "display": 10, "sort": "date"},
                headers={
                    "X-Naver-Client-Id": settings.naver_client_id,
                    "X-Naver-Client-Secret": settings.naver_client_secret,
                },
            )

        if response.status_code != 200:
            raise ValueError(f"Naver API 오류: {response.status_code}")

        data = response.json()
        return ScrapeResult(
            url_id=task.url_id,
            url=task.url,
            success=True,
            pipeline_name=self.name,
            pipeline_sequence=self.priority,
            pipelines_attempted=["api"],
            duration_ms=0,
            status_code=200,
            data=data,
            items_extracted=len(data.get("items", [])),
            method_details={"api": "naver_search"},
        )

    async def _call_kakao_api(self, task: ScrapeTask) -> ScrapeResult:
        if not settings.kakao_rest_api_key:
            raise ValueError("Kakao API 키가 설정되지 않았습니다.")

        parsed = urlparse(task.url)
        query = parsed.query or parsed.path.split("/")[-1] or ""

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                "https://dapi.kakao.com/v2/search/web",
                params={"query": query, "size": 10},
                headers={"Authorization": f"KakaoAK {settings.kakao_rest_api_key}"},
            )

        if response.status_code != 200:
            raise ValueError(f"Kakao API 오류: {response.status_code}")

        data = response.json()
        return ScrapeResult(
            url_id=task.url_id,
            url=task.url,
            success=True,
            pipeline_name=self.name,
            pipeline_sequence=self.priority,
            pipelines_attempted=["api"],
            duration_ms=0,
            status_code=200,
            data=data,
            items_extracted=len(data.get("documents", [])),
            method_details={"api": "kakao_search"},
        )

    async def _call_dart_api(self, task: ScrapeTask) -> ScrapeResult:
        if not settings.dart_api_key:
            raise ValueError("DART API 키가 설정되지 않았습니다.")

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                "https://opendart.fss.or.kr/api/list.json",
                params={"crtfc_key": settings.dart_api_key, "page_count": 10},
            )

        if response.status_code != 200:
            raise ValueError(f"DART API 오류: {response.status_code}")

        data = response.json()
        return ScrapeResult(
            url_id=task.url_id,
            url=task.url,
            success=True,
            pipeline_name=self.name,
            pipeline_sequence=self.priority,
            pipelines_attempted=["api"],
            duration_ms=0,
            status_code=200,
            data=data,
            items_extracted=len(data.get("list", [])),
            method_details={"api": "dart"},
        )

    async def _call_youtube_api(self, task: ScrapeTask) -> ScrapeResult:
        if not settings.youtube_api_key:
            raise ValueError("YouTube API 키가 설정되지 않았습니다.")

        # URL에서 video ID 추출
        parsed = urlparse(task.url)
        params: dict[str, Any] = {"key": settings.youtube_api_key}

        if "v=" in task.url:
            video_id = dict(p.split("=") for p in parsed.query.split("&") if "=" in p).get("v", "")
            endpoint = "https://www.googleapis.com/youtube/v3/videos"
            params.update({"id": video_id, "part": "snippet,statistics"})
        else:
            endpoint = "https://www.googleapis.com/youtube/v3/search"
            params.update({"q": parsed.path.split("/")[-1], "part": "snippet", "maxResults": 10})

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(endpoint, params=params)

        if response.status_code != 200:
            raise ValueError(f"YouTube API 오류: {response.status_code}")

        data = response.json()
        return ScrapeResult(
            url_id=task.url_id,
            url=task.url,
            success=True,
            pipeline_name=self.name,
            pipeline_sequence=self.priority,
            pipelines_attempted=["api"],
            duration_ms=0,
            status_code=200,
            data=data,
            items_extracted=len(data.get("items", [])),
            method_details={"api": "youtube"},
        )

    async def health_check(self, url: str) -> bool:
        """API 사용 가능 여부를 확인합니다."""
        return self._detect_api(url) is not None
