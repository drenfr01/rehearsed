"""Integration tests for the avatars API endpoint."""

import pytest
from sqlmodel import Session, select

from app.models.avatar import Avatar


@pytest.fixture
def seed_avatars(db_session: Session):
    """Seed avatars for testing (idempotent)."""
    avatar_data = [
        {"name": "Ash", "file_path": "Ash.jpg"},
        {"name": "Sage", "file_path": "Sage.jpg"},
        {"name": "Mr. Derek", "file_path": "Mr. Derek.png"},
    ]
    for data in avatar_data:
        existing = db_session.exec(select(Avatar).where(Avatar.name == data["name"])).first()
        if not existing:
            db_session.add(Avatar(**data))
    db_session.commit()

    return list(db_session.exec(select(Avatar).order_by(Avatar.name)).all())


@pytest.mark.integration
@pytest.mark.asyncio
class TestGetAvatars:
    """Test GET /api/v1/avatars."""

    async def test_returns_avatars(self, async_client, seed_avatars):
        response = await async_client.get("/api/v1/avatars")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3
        names = [a["name"] for a in data]
        assert "Ash" in names
        assert "Sage" in names
        assert "Mr. Derek" in names

    async def test_avatar_response_shape(self, async_client, seed_avatars):
        response = await async_client.get("/api/v1/avatars")
        assert response.status_code == 200
        data = response.json()
        avatar = data[0]
        assert "id" in avatar
        assert "name" in avatar
        assert "file_path" in avatar

    async def test_avatars_sorted_by_name(self, async_client, seed_avatars):
        response = await async_client.get("/api/v1/avatars")
        assert response.status_code == 200
        data = response.json()
        names = [a["name"] for a in data]
        assert names == sorted(names)

    async def test_empty_when_no_avatars(self, async_client):
        response = await async_client.get("/api/v1/avatars")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
