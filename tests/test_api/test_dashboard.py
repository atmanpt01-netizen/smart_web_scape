"""Tests for dashboard API endpoints."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_dashboard_summary(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/dashboard/summary")
    assert resp.status_code == 200
    data = resp.json()
    assert "total_urls" in data
    assert "active_urls" in data
    assert "success_rate" in data
    assert "today_items" in data


@pytest.mark.asyncio
async def test_success_rate_trend(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/dashboard/success-rate", params={"days": 7})
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)


@pytest.mark.asyncio
async def test_pipeline_stats(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/dashboard/pipeline-stats")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_category_stats(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/dashboard/category-stats")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_recent_visits(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/dashboard/recent-visits")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_alerts_list(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/dashboard/alerts")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_upcoming_schedules(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/dashboard/schedules/upcoming")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_mark_alert_read_not_found(client: AsyncClient) -> None:
    import uuid
    alert_id = str(uuid.uuid4())
    resp = await client.put(f"/api/v1/dashboard/alerts/{alert_id}/read")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_read_all_alerts(client: AsyncClient) -> None:
    resp = await client.post("/api/v1/dashboard/alerts/read-all")
    assert resp.status_code == 200
    data = resp.json()
    assert "updated" in data
