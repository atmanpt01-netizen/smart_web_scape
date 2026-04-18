"""Pipeline fallback chain integration tests."""

import pytest
from unittest.mock import AsyncMock, patch

from backend.api.schemas import ScrapeResult, ScrapeTask
from backend.core.orchestrator import PipelineOrchestrator


def _make_task(url: str = "https://example.com", category: str = "enterprise") -> ScrapeTask:
    return ScrapeTask(url=url, url_id=None, category=category, extraction_schema={})


def _success_result(pipeline: str) -> ScrapeResult:
    return ScrapeResult(
        url="https://example.com",
        success=True,
        pipeline_name=pipeline,
        data={},
        duration_ms=100,
    )


def _failure_result(pipeline: str, error: str = "timeout") -> ScrapeResult:
    return ScrapeResult(
        url="https://example.com",
        success=False,
        pipeline_name=pipeline,
        error_type=error,
        error_message=error,
        duration_ms=50,
    )


@pytest.mark.asyncio
async def test_first_pipeline_succeeds() -> None:
    """When the first pipeline succeeds, it returns without trying others."""
    orchestrator = PipelineOrchestrator()
    task = _make_task(category="enterprise")

    with patch.object(
        orchestrator.registry,
        "get_for_category",
        return_value=["http", "stealth"],
    ):
        http_mock = AsyncMock()
        http_mock.name = "http"
        http_mock.health_check = AsyncMock(return_value=True)
        http_mock.execute = AsyncMock(return_value=_success_result("http"))

        stealth_mock = AsyncMock()
        stealth_mock.name = "stealth"
        stealth_mock.health_check = AsyncMock(return_value=True)
        stealth_mock.execute = AsyncMock(return_value=_success_result("stealth"))

        orchestrator.registry.get_for_category = lambda cat: [http_mock, stealth_mock]

        result = await orchestrator.execute(task)

    assert result.success is True
    assert result.pipeline_name == "http"
    stealth_mock.execute.assert_not_called()


@pytest.mark.asyncio
async def test_fallback_to_second_pipeline() -> None:
    """When the first pipeline fails, the orchestrator tries the next one."""
    orchestrator = PipelineOrchestrator()
    task = _make_task(category="enterprise")

    http_mock = AsyncMock()
    http_mock.name = "http"
    http_mock.health_check = AsyncMock(return_value=True)
    http_mock.execute = AsyncMock(return_value=_failure_result("http"))

    stealth_mock = AsyncMock()
    stealth_mock.name = "stealth"
    stealth_mock.health_check = AsyncMock(return_value=True)
    stealth_mock.execute = AsyncMock(return_value=_success_result("stealth"))

    orchestrator.registry.get_for_category = lambda cat: [http_mock, stealth_mock]

    result = await orchestrator.execute(task)

    assert result.success is True
    assert result.pipeline_name == "stealth"


@pytest.mark.asyncio
async def test_all_pipelines_fail_returns_last_failure() -> None:
    """When all pipelines fail, the last failure result is returned."""
    orchestrator = PipelineOrchestrator()
    task = _make_task(category="enterprise")

    pipelines = []
    for name in ["http", "stealth", "ai"]:
        mock = AsyncMock()
        mock.name = name
        mock.health_check = AsyncMock(return_value=True)
        mock.execute = AsyncMock(return_value=_failure_result(name))
        pipelines.append(mock)

    orchestrator.registry.get_for_category = lambda cat: pipelines

    result = await orchestrator.execute(task)

    assert result.success is False
    assert result.pipeline_name == "ai"


@pytest.mark.asyncio
async def test_health_check_failure_skips_pipeline() -> None:
    """Pipelines that fail health_check are skipped."""
    orchestrator = PipelineOrchestrator()
    task = _make_task(category="enterprise")

    http_mock = AsyncMock()
    http_mock.name = "http"
    http_mock.health_check = AsyncMock(return_value=False)
    http_mock.execute = AsyncMock(return_value=_success_result("http"))

    stealth_mock = AsyncMock()
    stealth_mock.name = "stealth"
    stealth_mock.health_check = AsyncMock(return_value=True)
    stealth_mock.execute = AsyncMock(return_value=_success_result("stealth"))

    orchestrator.registry.get_for_category = lambda cat: [http_mock, stealth_mock]

    result = await orchestrator.execute(task)

    assert result.success is True
    assert result.pipeline_name == "stealth"
    http_mock.execute.assert_not_called()
