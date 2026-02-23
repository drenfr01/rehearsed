"""This file contains the agent voice seed data for the application."""

from sqlmodel import Session, select

from app.models.agent import AgentVoice
from app.services.database import database_service

AGENT_VOICES = [
    AgentVoice(voice_name="Achernar"),
    AgentVoice(voice_name="Achird"),
    AgentVoice(voice_name="Algenib"),
    AgentVoice(voice_name="Algieba"),
    AgentVoice(voice_name="Alnilam"),
    AgentVoice(voice_name="Aoede"),
    AgentVoice(voice_name="Autonoe"),
    AgentVoice(voice_name="Callirrhoe"),
    AgentVoice(voice_name="Charon"),
    AgentVoice(voice_name="Despina"),
    AgentVoice(voice_name="Enceladus"),
    AgentVoice(voice_name="Erinome"),
    AgentVoice(voice_name="Fenrir"),
    AgentVoice(voice_name="Gacrux"),
    AgentVoice(voice_name="Iapetus"),
    AgentVoice(voice_name="Kore"),
    AgentVoice(voice_name="Laomedeia"),
    AgentVoice(voice_name="Leda"),
    AgentVoice(voice_name="Orus"),
    AgentVoice(voice_name="Pulcherrima"),
    AgentVoice(voice_name="Puck"),
    AgentVoice(voice_name="Rasalgethi"),
    AgentVoice(voice_name="Sadachbia"),
    AgentVoice(voice_name="Sadaltager"),
    AgentVoice(voice_name="Schedar"),
    AgentVoice(voice_name="Sulafat"),
    AgentVoice(voice_name="Umbriel"),
    AgentVoice(voice_name="Vindemiatrix"),
    AgentVoice(voice_name="Zephyr"),
    AgentVoice(voice_name="Zubenelgenubi"),
]


def seed_agent_voice_data():
    """Seed the agent voice data into the database."""
    with Session(database_service.engine) as session:
        # Check if any voices already exist
        voices_exist = session.exec(select(AgentVoice)).first()
        if voices_exist:
            return
        for voice in AGENT_VOICES:
            session.add(voice)
        session.commit()
