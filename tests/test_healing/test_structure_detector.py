"""Tests for L2 Self-Healing: StructureDetector."""

import xxhash
import pytest
from unittest.mock import AsyncMock, patch

from backend.healing.structure_detector import StructureDetector


def _hash(content: str) -> str:
    return xxhash.xxh64(content.encode()).hexdigest()


def test_hash_differs_when_content_changes() -> None:
    """Different HTML produces different hashes."""
    html_v1 = "<html><body><div class='a'>Old</div></body></html>"
    html_v2 = "<html><body><section class='b'>New</section></body></html>"
    assert _hash(html_v1) != _hash(html_v2)


def test_hash_stable_for_same_content() -> None:
    """Same HTML always produces the same hash."""
    html = "<html><body><div>Content</div></body></html>"
    assert _hash(html) == _hash(html)


@pytest.mark.asyncio
async def test_fetch_page_called_in_detect_and_adapt() -> None:
    """detect_and_adapt fetches the target page."""
    detector = StructureDetector()

    from backend.api.schemas import ScrapeTask
    task = ScrapeTask(
        url="https://example.com",
        url_id=None,
        category="enterprise",
        extraction_schema={"title": "h1"},
    )

    with patch.object(detector, "_fetch_page", new_callable=AsyncMock) as mock_fetch:
        mock_fetch.return_value = None  # simulate fetch failure
        result = await detector.detect_and_adapt(task)

    mock_fetch.assert_called_once_with(task.url)
    assert result.success is False
    assert "실패" in result.message


@pytest.mark.asyncio
async def test_detect_fails_gracefully_when_llm_unavailable() -> None:
    """When LLM is unavailable, detect_and_adapt returns a failure HealingResult."""
    detector = StructureDetector()

    from backend.api.schemas import ScrapeTask
    task = ScrapeTask(
        url="https://example.com",
        url_id=None,
        category="enterprise",
        extraction_schema={"title": "h1"},
    )
    html = "<html><body><h1>New Title</h1></body></html>"

    with patch.object(detector, "_fetch_page", new_callable=AsyncMock, return_value=html):
        with patch.object(detector, "_page_to_markdown", new_callable=AsyncMock, return_value="# New Title"):
            with patch.object(detector, "_llm_analyze_structure", new_callable=AsyncMock, return_value=None):
                result = await detector.detect_and_adapt(task)

    assert result.success is False
