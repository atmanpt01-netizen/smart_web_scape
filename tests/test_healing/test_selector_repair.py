"""Tests for L1 Self-Healing: SelectorRepair."""

import pytest
from unittest.mock import AsyncMock, patch

from backend.healing.selector_repair import SelectorRepair


def test_generate_candidates_from_class_selector() -> None:
    """Class-based selectors produce variant candidates."""
    repair = SelectorRepair()
    candidates = repair._generate_selector_candidates(".article-title")
    assert len(candidates) > 0
    assert any("article" in c.lower() or "title" in c.lower() for c in candidates)


def test_generate_candidates_from_id_selector() -> None:
    """ID-based selectors produce candidates based on the tag part."""
    repair = SelectorRepair()
    candidates = repair._generate_selector_candidates("#main-content")
    assert len(candidates) > 0


def test_generate_candidates_compound_selector() -> None:
    """Multi-class selectors produce partial-match candidates."""
    repair = SelectorRepair()
    candidates = repair._generate_selector_candidates(".news.article")
    assert len(candidates) > 0


@pytest.mark.asyncio
async def test_fetch_page_returns_content() -> None:
    """_fetch_page returns HTML string on success."""
    repair = SelectorRepair()
    html = "<html><body><div class='title'>Hello</div></body></html>"

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.text = html
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client_cls.return_value = mock_client

        result = await repair._fetch_page("https://example.com")

    assert result == html
