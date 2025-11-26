"""Simple script to create a user for local development."""

import asyncio
from app.models.user import User
from app.services.database import DatabaseService


async def create_user():
    """Create a test user."""
    db = DatabaseService()
    
    # User credentials - change these as needed
    email = "megan@example.com"
    password = "meg123"  # Must meet requirements: 8+ chars, uppercase, lowercase, number, special char
    
    # Check if user already exists
    existing_user = await db.get_user_by_email(email)
    if existing_user:
        print(f"User {email} already exists!")
        print(f"User ID: {existing_user.id}")
        print(f"Is Admin: {existing_user.is_admin}")
        return
    
    # Hash password and create user
    hashed_password = User.hash_password(password)
    user = await db.create_user(email, hashed_password)
    
    print(f"✅ User created successfully!")
    print(f"Email: {email}")
    print(f"Password: {password}")
    print(f"User ID: {user.id}")
    print(f"Is Admin: {user.is_admin}")
    print(f"\nYou can now log in at the frontend with these credentials.")


if __name__ == "__main__":
    asyncio.run(create_user())
