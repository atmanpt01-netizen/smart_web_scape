"""Tests for JWT authentication endpoints."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient) -> None:
    resp = await client.post("/api/v1/auth/login", json={"username": "admin", "password": "admin1234"})
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient) -> None:
    resp = await client.post("/api/v1/auth/login", json={"username": "admin", "password": "wrong"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_login_unknown_user(client: AsyncClient) -> None:
    resp = await client.post("/api/v1/auth/login", json={"username": "nobody", "password": "x"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_refresh_token(client: AsyncClient) -> None:
    login_resp = await client.post(
        "/api/v1/auth/login", json={"username": "admin", "password": "admin1234"}
    )
    refresh_token = login_resp.json()["refresh_token"]

    resp = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data


@pytest.mark.asyncio
async def test_refresh_with_access_token_fails(client: AsyncClient) -> None:
    login_resp = await client.post(
        "/api/v1/auth/login", json={"username": "admin", "password": "admin1234"}
    )
    access_token = login_resp.json()["access_token"]

    # Using access token as refresh token should fail
    resp = await client.post("/api/v1/auth/refresh", json={"refresh_token": access_token})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_refresh_invalid_token(client: AsyncClient) -> None:
    resp = await client.post("/api/v1/auth/refresh", json={"refresh_token": "invalid.token.here"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_logout(client: AsyncClient) -> None:
    resp = await client.post("/api/v1/auth/logout")
    assert resp.status_code == 204
