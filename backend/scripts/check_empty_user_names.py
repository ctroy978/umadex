"""Script to check for users with empty first or last names"""
import asyncio
from sqlalchemy import select, or_, and_
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db, engine
from app.models.user import User

async def check_empty_names():
    """Check for users with empty or null names"""
    async with AsyncSession(engine) as db:
        # Query for users with empty or null names
        query = select(User).where(
            and_(
                User.deleted_at.is_(None),  # Only active users
                or_(
                    User.first_name.is_(None),
                    User.first_name == '',
                    User.last_name.is_(None),
                    User.last_name == ''
                )
            )
        )
        
        result = await db.execute(query)
        users_with_empty_names = result.scalars().all()
        
        if not users_with_empty_names:
            print("✅ No users found with empty names!")
            return
        
        print(f"⚠️  Found {len(users_with_empty_names)} users with empty names:\n")
        
        for user in users_with_empty_names:
            print(f"User ID: {user.id}")
            print(f"Email: {user.email}")
            print(f"First Name: '{user.first_name}' (empty: {not user.first_name})")
            print(f"Last Name: '{user.last_name}' (empty: {not user.last_name})")
            print(f"Role: {user.role}")
            print(f"Created: {user.created_at}")
            print("-" * 50)
        
        print(f"\nTotal affected users: {len(users_with_empty_names)}")
        print("\nThe migration script will automatically fix these by:")
        print("- Setting first_name to the part before @ in email")
        print("- Setting last_name to 'User'")

if __name__ == "__main__":
    asyncio.run(check_empty_names())