"""Supabase authentication service"""
from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.user import User, UserRole
from app.core.supabase import get_supabase_admin, get_supabase_anon
from app.core.config import settings
from app.schemas.user import UserCreate
from app.models.auth import EmailWhitelist as Whitelist
import logging

logger = logging.getLogger(__name__)

class SupabaseAuthService:
    @staticmethod
    async def check_whitelist(db: AsyncSession, email: str) -> bool:
        """Check if email is in whitelist"""
        # Check exact email match
        exact_result = await db.execute(
            select(Whitelist).where(
                Whitelist.email_pattern == email,
                Whitelist.is_domain == False
            )
        )
        if exact_result.scalar_one_or_none():
            return True
            
        # Check domain match
        domain = email.split('@')[1] if '@' in email else None
        if domain:
            domain_result = await db.execute(
                select(Whitelist).where(
                    Whitelist.email_pattern == domain,
                    Whitelist.is_domain == True
                )
            )
            if domain_result.scalar_one_or_none():
                return True
                
        return False
    
    @staticmethod
    async def request_otp(db: AsyncSession, email: str, user_data: Optional[UserCreate] = None) -> Dict[str, Any]:
        """Request OTP for email"""
        supabase = get_supabase_anon()
        
        # Check whitelist
        if not await SupabaseAuthService.check_whitelist(db, email):
            raise ValueError("Email not in whitelist")
        
        # Check if user exists in our database
        result = await db.execute(
            select(User).where(User.email == email, User.deleted_at.is_(None))
        )
        existing_user = result.scalar_one_or_none()
        
        # Check if user exists in Supabase Auth
        supabase_admin = get_supabase_admin()
        try:
            auth_users = supabase_admin.auth.admin.list_users()
            supabase_user = next((u for u in auth_users if u.email == email), None)
        except:
            supabase_user = None
        
        # If user exists in Supabase but not in our DB, and no user data provided
        if not existing_user and supabase_user and not user_data:
            # For existing Supabase users without local user record, 
            # we still need user data to create the local record
            raise ValueError("User data required for new users")
        
        try:
            # Send OTP via Supabase
            response = supabase.auth.sign_in_with_otp({
                "email": email,
                "options": {
                    "should_create_user": not existing_user,
                    "email_redirect_to": None,  # Disable magic link
                    "data": {
                        "first_name": user_data.first_name if user_data else "",
                        "last_name": user_data.last_name if user_data else "",
                        "role": user_data.role if user_data else "student",
                        "is_admin": False  # Never set admin on signup
                    } if not existing_user and user_data else None
                }
            })
            
            return {
                "message": "OTP sent successfully",
                "email": email,
                "is_new_user": not existing_user
            }
            
        except Exception as e:
            logger.error(f"Failed to send OTP: {str(e)}")
            raise ValueError("Failed to send OTP")
    
    @staticmethod
    async def verify_otp(db: AsyncSession, email: str, otp: str) -> Dict[str, Any]:
        """Verify OTP and create/update user"""
        supabase = get_supabase_anon()
        
        try:
            # Verify OTP with Supabase
            response = supabase.auth.verify_otp({
                "email": email,
                "token": otp,
                "type": "email"
            })
            
            if not response.user:
                raise ValueError("Invalid OTP")
            
            auth_user = response.user
            session = response.session
            
            # Get or create user in our database
            result = await db.execute(
                select(User).where(User.email == email)
            )
            user = result.scalar_one_or_none()
            
            if not user:
                # Create new user
                user = User(
                    email=email,
                    username=email,  # Default username to email
                    first_name=auth_user.user_metadata.get("first_name", ""),
                    last_name=auth_user.user_metadata.get("last_name", ""),
                    role=UserRole(auth_user.user_metadata.get("role", UserRole.STUDENT.value)),
                    is_admin=auth_user.user_metadata.get("is_admin", False),
                    supabase_auth_id=auth_user.id
                )
                db.add(user)
            else:
                # Update existing user with Supabase Auth ID if not set
                if not user.supabase_auth_id:
                    user.supabase_auth_id = auth_user.id
                    
                # Update user metadata in Supabase to match our database
                supabase_admin = get_supabase_admin()
                supabase_admin.auth.admin.update_user_by_id(
                    auth_user.id,
                    {
                        "user_metadata": {
                            "id": str(user.id),
                            "role": user.role,
                            "is_admin": user.is_admin,
                            "first_name": user.first_name,
                            "last_name": user.last_name
                        }
                    }
                )
            
            await db.commit()
            await db.refresh(user)
            
            return {
                "access_token": session.access_token,
                "refresh_token": session.refresh_token,
                "token_type": "bearer",
                "expires_in": 3600,  # Default to 1 hour
                "user": {
                    "id": str(user.id),
                    "email": user.email,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "username": user.username,
                    "role": user.role,
                    "is_admin": user.is_admin,
                    "created_at": user.created_at
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to verify OTP: {str(e)}")
            raise ValueError("Invalid or expired OTP")
    
    @staticmethod
    async def refresh_token(refresh_token: str) -> Dict[str, Any]:
        """Refresh access token"""
        supabase = get_supabase_anon()
        
        try:
            response = supabase.auth.refresh_session(refresh_token)
            
            if not response.session:
                raise ValueError("Invalid refresh token")
            
            return {
                "access_token": response.session.access_token,
                "refresh_token": response.session.refresh_token,
                "token_type": "bearer"
            }
            
        except Exception as e:
            logger.error(f"Failed to refresh token: {str(e)}")
            raise ValueError("Invalid or expired refresh token")
    
    @staticmethod
    async def logout(access_token: str) -> None:
        """Logout user"""
        supabase = get_supabase_anon()
        
        try:
            # Set the session to use the user's token
            supabase.auth.set_session(access_token, "")
            supabase.auth.sign_out()
        except Exception as e:
            logger.error(f"Failed to logout: {str(e)}")
            # Don't raise error on logout failure
    
    @staticmethod
    async def get_user_from_token(db: AsyncSession, access_token: str) -> Optional[User]:
        """Get user from Supabase access token"""
        supabase = get_supabase_anon()
        
        try:
            logger.info(f"Attempting to validate token of length: {len(access_token) if access_token else 0}")
            
            # Get user from token
            response = supabase.auth.get_user(access_token)
            
            if not response.user:
                logger.error(f"No user found for token validation - Supabase returned no user")
                return None
            
            logger.info(f"Supabase returned user: {response.user.email} with ID: {response.user.id}")
            
            # Get user from database by Supabase Auth ID
            result = await db.execute(
                select(User).where(
                    User.supabase_auth_id == response.user.id,
                    User.deleted_at.is_(None)
                )
            )
            user = result.scalar_one_or_none()
            
            if user:
                logger.info(f"Found user by supabase_auth_id: {user.email}")
            else:
                logger.info(f"No user found by supabase_auth_id, trying email fallback")
            
            # Fallback to email if supabase_auth_id not set (during migration)
            if not user:
                result = await db.execute(
                    select(User).where(
                        User.email == response.user.email,
                        User.deleted_at.is_(None)
                    )
                )
                user = result.scalar_one_or_none()
                
                if user:
                    logger.info(f"Found user by email fallback: {user.email}")
                    # Update supabase_auth_id if found by email
                    if not user.supabase_auth_id:
                        user.supabase_auth_id = response.user.id
                        await db.commit()
                        logger.info(f"Updated supabase_auth_id for user: {user.email}")
                else:
                    logger.error(f"No user found in database for email: {response.user.email}")
            
            return user
            
        except Exception as e:
            logger.error(f"Failed to get user from token: {str(e)} - Token length: {len(access_token) if access_token else 0}")
            logger.exception("Full exception details:")
            return None