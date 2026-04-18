import uuid

import pytest
import respx
from httpx import Response

from backend.api.schemas import ScrapeTask
from backend.pipelines.http_pipeline import HttpPipeline


@pytest.fixture
def task() -> ScrapeTask:
    return ScrapeTask(
        url_id=uuid.uuid4(),
        url="https://example.com",
        category="enterprise",
        extraction_schema={"title": "h1", "description": "p"},
    )


@pytest.fixture
def pipeline() -> HttpPipeline:
    return HttpPipeline()


@pytest.mark.asyncio
class TestHttpPipeline:
    @respx.mock
    async def test_successful_fetch(self, pipeline: HttpPipeline, task: ScrapeTask) -> None:
        """정상 HTML 응답 시 수집이 성공합니다."""
        html = "<html><body><h1>테스트 제목</h1><p>테스트 내용</p></body></html>"
        respx.get("https://example.com").mock(return_value=Response(200, text=html))

        result = await pipeline.execute(task)

        assert result.success is True
        assert result.pipeline_name == "http"
        assert result.status_code == 200
        assert result.data is not None
        assert result.data.get("title") == "테스트 제목"
        assert result.content_hash is not None
        assert result.duration_ms >= 0

    @respx.mock
    async def test_403_returns_failure(self, pipeline: HttpPipeline, task: ScrapeTask) -> None:
        """403 응답 시 실패를 반환하고 antibot_detected를 설정합니다."""
        respx.get("https://example.com").mock(return_value=Response(403))

        result = await pipeline.execute(task)

        assert result.success is False
        assert result.status_code == 403
        assert result.antibot_detected == "http_403"

    @respx.mock
    async def test_empty_extraction_schema(self, pipeline: HttpPipeline) -> None:
        """extraction_schema 없이도 정상 수집됩니다."""
        html = "<html><body><h1>제목</h1></body></html>"
        respx.get("https://example.com").mock(return_value=Response(200, text=html))

        task = ScrapeTask(
            url_id=uuid.uuid4(),
            url="https://example.com",
            category="enterprise",
            extraction_schema=None,
        )
        result = await pipeline.execute(task)

        assert result.success is True
        assert result.data == {}

    @respx.mock
    async def test_content_hash_calculated(self, pipeline: HttpPipeline, task: ScrapeTask) -> None:
        """수집 성공 시 content_hash가 계산됩니다."""
        html = "<html><body><h1>제목</h1></body></html>"
        respx.get("https://example.com").mock(return_value=Response(200, text=html))

        result = await pipeline.execute(task)

        assert result.content_hash is not None
        assert len(result.content_hash) == 16  # xxhash64 hexdigest

    async def test_health_check_unreachable(self, pipeline: HttpPipeline) -> None:
        """연결 불가 URL에 대한 health check는 False를 반환합니다."""
        result = await pipeline.health_check("https://this-domain-does-not-exist-12345.com")
        assert result is False
