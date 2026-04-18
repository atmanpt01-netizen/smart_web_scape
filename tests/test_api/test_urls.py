import pytest
from httpx import AsyncClient
from unittest.mock import patch


@pytest.mark.asyncio
class TestUrlRegistration:
    async def test_register_single_url(self, client: AsyncClient) -> None:
        """단일 URL 등록이 정상 동작합니다."""
        with patch("backend.utils.robots_checker.check_robots_txt", return_value=True):
            response = await client.post(
                "/api/v1/urls",
                json={
                    "url": "https://example.com/news",
                    "name": "예제 뉴스",
                    "extraction_schema": {"title": "h1", "content": "article"},
                },
            )

        assert response.status_code == 201
        data = response.json()
        assert data["url"] == "https://example.com/news"
        assert data["name"] == "예제 뉴스"
        assert data["category"] == "enterprise"  # 기본값
        assert "id" in data

    async def test_auto_categorize_naver(self, client: AsyncClient) -> None:
        """Naver URL은 portal로 자동 분류됩니다."""
        with patch("backend.utils.robots_checker.check_robots_txt", return_value=True):
            response = await client.post(
                "/api/v1/urls",
                json={"url": "https://news.naver.com/main"},
            )

        assert response.status_code == 201
        assert response.json()["category"] == "portal"

    async def test_auto_categorize_government(self, client: AsyncClient) -> None:
        """gov.kr URL은 government로 자동 분류됩니다."""
        with patch("backend.utils.robots_checker.check_robots_txt", return_value=True):
            response = await client.post(
                "/api/v1/urls",
                json={"url": "https://www.mois.go.kr/frt/main"},
            )

        assert response.status_code == 201
        assert response.json()["category"] == "government"

    async def test_register_duplicate_url_returns_409(self, client: AsyncClient) -> None:
        """중복 URL 등록 시 409를 반환합니다."""
        with patch("backend.utils.robots_checker.check_robots_txt", return_value=True):
            await client.post("/api/v1/urls", json={"url": "https://example.com"})
            response = await client.post("/api/v1/urls", json={"url": "https://example.com"})

        assert response.status_code == 409

    async def test_robots_disallowed_returns_403(self, client: AsyncClient) -> None:
        """robots.txt 차단 URL 등록 시 403을 반환합니다."""
        with patch("backend.utils.robots_checker.check_robots_txt", return_value=False):
            response = await client.post(
                "/api/v1/urls",
                json={"url": "https://restricted-site.com"},
            )

        assert response.status_code == 403

    async def test_invalid_url_format(self, client: AsyncClient) -> None:
        """잘못된 URL 형식 시 422를 반환합니다."""
        response = await client.post("/api/v1/urls", json={"url": "not-a-url"})
        assert response.status_code == 422


@pytest.mark.asyncio
class TestUrlCrud:
    async def _register_url(self, client: AsyncClient, url: str = "https://example.com") -> dict:
        with patch("backend.utils.robots_checker.check_robots_txt", return_value=True):
            r = await client.post("/api/v1/urls", json={"url": url})
        return r.json()

    async def test_list_urls(self, client: AsyncClient) -> None:
        """URL 목록 조회가 정상 동작합니다."""
        await self._register_url(client, "https://example.com")
        await self._register_url(client, "https://example.org")

        response = await client.get("/api/v1/urls")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert len(data["items"]) == 2

    async def test_list_urls_filter_category(self, client: AsyncClient) -> None:
        """카테고리 필터 조회가 정상 동작합니다."""
        with patch("backend.utils.robots_checker.check_robots_txt", return_value=True):
            await client.post("/api/v1/urls", json={"url": "https://news.naver.com"})
            await client.post("/api/v1/urls", json={"url": "https://example.com"})

        response = await client.get("/api/v1/urls?category=portal")
        assert response.status_code == 200
        assert response.json()["total"] == 1

    async def test_get_url_by_id(self, client: AsyncClient) -> None:
        """ID로 URL 단건 조회가 정상 동작합니다."""
        created = await self._register_url(client)
        url_id = created["id"]

        response = await client.get(f"/api/v1/urls/{url_id}")
        assert response.status_code == 200
        assert response.json()["id"] == url_id

    async def test_get_url_not_found(self, client: AsyncClient) -> None:
        """존재하지 않는 URL 조회 시 404를 반환합니다."""
        import uuid
        response = await client.get(f"/api/v1/urls/{uuid.uuid4()}")
        assert response.status_code == 404

    async def test_update_url(self, client: AsyncClient) -> None:
        """URL 수정이 정상 동작합니다."""
        created = await self._register_url(client)
        url_id = created["id"]

        response = await client.put(
            f"/api/v1/urls/{url_id}",
            json={"name": "수정된 이름", "is_active": False},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "수정된 이름"
        assert data["is_active"] is False

    async def test_delete_url(self, client: AsyncClient) -> None:
        """URL 삭제가 정상 동작합니다."""
        created = await self._register_url(client)
        url_id = created["id"]

        response = await client.delete(f"/api/v1/urls/{url_id}")
        assert response.status_code == 204

        # 삭제 후 조회 시 404
        response = await client.get(f"/api/v1/urls/{url_id}")
        assert response.status_code == 404

    async def test_list_urls_pagination(self, client: AsyncClient) -> None:
        """페이지네이션이 정상 동작합니다."""
        for i in range(5):
            await self._register_url(client, f"https://example{i}.com")

        response = await client.get("/api/v1/urls?page=1&size=2")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 5
        assert len(data["items"]) == 2
        assert data["pages"] == 3
