"""Seed data for student avatars."""

from sqlmodel import Session, select

from app.models.avatar import Avatar
from app.services.database import database_service

AVATAR_DATA = [
    {"name": "Ash", "file_path": "Ash.jpg"},
    {"name": "Chipper", "file_path": "Chipper.jpg"},
    {"name": "Dart", "file_path": "Dart.jpg"},
    {"name": "Mr. Damian", "file_path": "Mr. Damian.jpg"},
    {"name": "Mr. David", "file_path": "Mr. David.jpg"},
    {"name": "Mr. Derek", "file_path": "Mr. Derek.png"},
    {"name": "Ms. Daria", "file_path": "Ms. Daria.jpg"},
    {"name": "Ms. Desiree", "file_path": "Ms. Desiree.jpg"},
    {"name": "Mx. Dylan", "file_path": "Mx. Dylan.jpg"},
    {"name": "Pip", "file_path": "Pip.jpg"},
    {"name": "Puck", "file_path": "Puck.jpg"},
    {"name": "Riven", "file_path": "Riven.jpg"},
    {"name": "Rook", "file_path": "Rook.jpg"},
    {"name": "Sage", "file_path": "Sage.jpg"},
    {"name": "Vex", "file_path": "Vex.jpg"},
    {"name": "Wren", "file_path": "Wren.jpg"},
]


def seed_avatar_data():
    """Seed the avatar table with available student avatars."""
    with Session(database_service.engine) as session:
        existing = session.exec(select(Avatar)).first()
        if existing:
            return

        for avatar_info in AVATAR_DATA:
            avatar = Avatar(name=avatar_info["name"], file_path=avatar_info["file_path"])
            session.add(avatar)

        session.commit()
