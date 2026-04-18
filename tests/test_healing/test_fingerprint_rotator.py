"""Tests for L3 Self-Healing: FingerprintRotator."""

import asyncio
import pytest
from unittest.mock import AsyncMock, patch

from backend.api.schemas import ScrapeResult, ScrapeTask
from backend.healing.fingerprint_rotator import FingerprintRotator
from backend.healing.engine import ScrapeError


def _make_task(url: str = "https://example.com") -> ScrapeTask:
    return ScrapeTask(url=url, url_id=None, category="enterprise", extraction_schema={})


def _make_error(msg: str = "cloudflare") -> ScrapeError:
    return ScrapeError(type="blocked", message=msg)


def _ok_result(url: str = "https://example.com") -> ScrapeResult:
    return ScrapeResult(url=url, success=True, pipeline_name="http", data={}, duration_ms=200)


def _fail_result(url: str = "https://example.com") -> ScrapeResult:
    return ScrapeResult(url=url, success=False, pipeline_name="http", error_type="blocked", duration_ms=50)


def test_detect_strategy_cloudflare() -> None:
    """Cloudflare antibot hint should return ≥5s delay strategy."""
    rotator = FingerprintRotator()
    strategy = rotator._detect_strategy("cloudflare challenge")
    assert strategy["delay_ms"] >= 5000


def test_detect_strategy_unknown_returns_default() -> None:
    """Unknown antibot type should return a default strategy without crashing."""
    rotator = FingerprintRotator()
    strategy = rotator._detect_strategy("unknown_vendor_xyz")
    assert "delay_ms" in strategy


@pytest.mark.asyncio
async def test_rotate_succeeds_on_cffi_retry() -> None:
    """rotate_and_retry returns success when _retry_with_cffi succeeds."""
    rotator = FingerprintRotator()
    task = _make_task()
    error = _make_error("cloudflare")

    with patch("asyncio.sleep", new_callable=AsyncMock):
        with patch.object(rotator, "_retry_with_cffi", new_callable=AsyncMock, return_value=_ok_result()):
            result = await rotator.rotate_and_retry(task, error)

    assert result.success is True
    assert result.healing_type == "fingerprint_rotation"


@pytest.mark.asyncio
async def test_rotate_falls_back_to_stealth_on_cffi_failure() -> None:
    """rotate_and_retry tries Stealth pipeline when cffi retry fails."""
    rotator = FingerprintRotator()
    task = _make_task()
    error = _make_error("datadome")

    stealth_result = _ok_result()

    with patch("asyncio.sleep", new_callable=AsyncMock):
        with patch.object(rotator, "_retry_with_cffi", new_callable=AsyncMock, return_value=_fail_result()):
            with patch(
                "backend.pipelines.stealth_pipeline.StealthPipeline.execute",
                new_callable=AsyncMock,
                return_value=stealth_result,
            ):
                result = await rotator.rotate_and_retry(task, error)

    assert result.success is True


@pytest.mark.asyncio
async def test_rotate_returns_failure_when_all_fail() -> None:
    """rotate_and_retry returns failure HealingResult when both cffi and stealth fail."""
    rotator = FingerprintRotator()
    task = _make_task()
    error = _make_error("akamai")

    with patch("asyncio.sleep", new_callable=AsyncMock):
        with patch.object(rotator, "_retry_with_cffi", new_callable=AsyncMock, return_value=_fail_result()):
            with patch(
                "backend.pipelines.stealth_pipeline.StealthPipeline.execute",
                new_callable=AsyncMock,
                return_value=_fail_result(),
            ):
                result = await rotator.rotate_and_retry(task, error)

    assert result.success is False
