"""Main database service singleton."""

from app.services.database.base import DatabaseService

# Create a singleton instance
database_service = DatabaseService()
