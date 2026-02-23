"""Dependencies for API endpoints.

This module provides dependency injection functions for common services
used across API routes.
"""

from fastapi import Depends

from app.services.database import database_service
from app.services.database.base import DatabaseService
from app.services.gemini_text_to_speech import GeminiTextToSpeech

# Create a singleton instance
text_to_speech_service = GeminiTextToSpeech()


def get_database_service() -> DatabaseService:
    """Get the singleton database service instance.
    
    Returns:
        DatabaseService: The singleton database service instance.
    """
    return database_service


def get_text_to_speech_service() -> GeminiTextToSpeech:
    """Get the singleton text-to-speech service instance.
    
    Returns:
        GeminiTextToSpeech: The singleton text-to-speech service instance.
    """
    return text_to_speech_service
