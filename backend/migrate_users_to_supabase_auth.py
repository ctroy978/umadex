"""
Script to migrate existing users to Supabase Auth
This creates Supabase Auth users for all existing users in the database
"""
import asyncio
from sqlalchemy import select
from app.core.database import SessionLocal
from app.models.user import User
from app.core.supabase import get_supabase_admin
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def migrate_users_to_supabase_auth():
    """Migrate existing users to Supabase Auth"""
    db = SessionLocal()
    supabase = get_supabase_admin()
    
    try:
        # Get all active users
        result = await db.execute(
            select(User).where(User.deleted_at.is_(None))
        )
        users = result.scalars().all()
        
        logger.info(f"Found {len(users)} users to migrate")
        
        migrated = 0
        errors = []
        
        for user in users:
            try:
                # Create user in Supabase Auth
                # Note: We can't set passwords, users will need to use OTP on first login
                auth_user = supabase.auth.admin.create_user({
                    "email": user.email,
                    "email_confirm": True,  # Auto-confirm email since they're existing users
                    "user_metadata": {
                        "id": str(user.id),
                        "role": user.role,
                        "is_admin": user.is_admin,
                        "first_name": user.first_name,
                        "last_name": user.last_name
                    }
                })
                
                # Update user record with Supabase Auth ID
                user.supabase_auth_id = auth_user.user.id
                await db.commit()
                
                migrated += 1
                logger.info(f"Migrated user: {user.email}")
                
            except Exception as e:
                error_msg = f"Failed to migrate user {user.email}: {str(e)}"
                logger.error(error_msg)
                errors.append(error_msg)
                # Continue with next user
                
        logger.info(f"Migration complete. Migrated: {migrated}, Errors: {len(errors)}")
        
        if errors:
            logger.error("Errors during migration:")
            for error in errors:
                logger.error(error)
                
    except Exception as e:
        logger.error(f"Migration failed: {str(e)}")
        raise
    finally:
        await db.close()

if __name__ == "__main__":
    asyncio.run(migrate_users_to_supabase_auth())