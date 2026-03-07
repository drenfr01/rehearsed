"""Unit tests for Avatar model."""

from datetime import datetime

import pytest

from app.models.avatar import Avatar


@pytest.mark.unit
class TestAvatar:
    """Test Avatar model."""

    def test_create_avatar(self):
        avatar = Avatar(name="Ash", file_path="Ash.jpg")
        assert avatar.name == "Ash"
        assert avatar.file_path == "Ash.jpg"
        assert avatar.id is None

    def test_has_created_at(self):
        avatar = Avatar(name="Sage", file_path="Sage.jpg")
        assert avatar.created_at is not None
        assert isinstance(avatar.created_at, datetime)

    def test_different_file_extensions(self):
        jpg_avatar = Avatar(name="Ash", file_path="Ash.jpg")
        png_avatar = Avatar(name="Mr. Derek", file_path="Mr. Derek.png")
        assert jpg_avatar.file_path.endswith(".jpg")
        assert png_avatar.file_path.endswith(".png")
