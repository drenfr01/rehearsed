"""Dependencies for API endpoints.

This module provides dependency injection functions for common services
used across API routes.
"""

from fastapi import Depends
from app.services.database import database_service
from app.services.database.base import DatabaseService


def get_database_service() -> DatabaseService:
    """Get the singleton database service instance.
    
    Returns:
        DatabaseService: The singleton database service instance.
    """
    return database_service
