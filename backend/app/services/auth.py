from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session
from sqlalchemy import select, and_, or_, text
from uuid import UUID
import json

from app.models import User, EmailWhitelist, OTPRequest, UserSession, RefreshToken
from app.core.security import (
    generate_otp, generate_session_token, create_token_pair,
    hash_refresh_token, verify_access_token, create_access_token
)
from app.core.redis import redis_client
from app.core.config import settings

class AuthService:
    @staticmethod
    async def check_email_whitelist(db: AsyncSession, email: str) -> bool:
        """Check if email is whitelisted"""
        # Check exact email match
        result = await db.execute(
            select(EmailWhitelist).where(
                and_(
                    EmailWhitelist.email_pattern == email,
                    EmailWhitelist.is_domain == False
                )
            )
        )
        if result.scalar_one_or_none():
            return True
        
        # Check domain match
        domain = email.split('@')[1] if '@' in email else None
        if domain:
            result = await db.execute(
                select(EmailWhitelist).where(
                    and_(
                        EmailWhitelist.email_pattern == domain,
                        EmailWhitelist.is_domain == True
                    )
                )
            )
            if result.scalar_one_or_none():
                return True
        
        return False
    
    @staticmethod
    async def generate_and_store_otp(email: str) -> str:
        """Generate OTP and store in Redis"""
        otp = generate_otp(settings.OTP_LENGTH)
        key = f"otp:{email}"
        expiry_seconds = settings.OTP_EXPIRY_MINUTES * 60
        
        await redis_client.set_with_expiry(key, otp, expiry_seconds)
        return otp
    
    @staticmethod
    async def verify_otp(email: str, otp_code: str) -> bool:
        """Verify OTP from Redis"""
        key = f"otp:{email}"
        stored_otp = await redis_client.get(key)
        
        if stored_otp and stored_otp == otp_code:
            await redis_client.delete(key)
            return True
        
        return False
    
    @staticmethod
    async def create_session(db: AsyncSession, user_id: UUID) -> str:
        """Create user session and return token"""
        token = generate_session_token()
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        
        session = UserSession(
            user_id=user_id,
            token=token,
            expires_at=expires_at
        )
        db.add(session)
        await db.commit()
        
        return token
    
    @staticmethod
    async def get_user_by_token(db: AsyncSession, token: str) -> Optional[User]:
        """Get user by session token"""
        result = await db.execute(
            select(User).join(UserSession).where(
                and_(
                    UserSession.token == token,
                    UserSession.expires_at > datetime.now(timezone.utc),
                    User.deleted_at.is_(None)  # Exclude soft deleted users
                )
            )
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    async def invalidate_session(db: AsyncSession, token: str):
        """Invalidate user session"""
        result = await db.execute(
            select(UserSession).where(UserSession.token == token)
        )
        session = result.scalar_one_or_none()
        if session:
            await db.delete(session)
            await db.commit()
    
    @staticmethod
    async def create_token_pair_for_user(
        db: AsyncSession, 
        user_id: UUID,
        device_info: Optional[Dict[str, Any]] = None
    ) -> Tuple[str, str, datetime, datetime]:
        """Create JWT access/refresh token pair for user"""
        access_token, refresh_token, access_expiry, refresh_expiry = create_token_pair(str(user_id))
        
        # Store refresh token hash in database
        refresh_token_hash = hash_refresh_token(refresh_token)
        refresh_token_model = RefreshToken(
            user_id=user_id,
            token_hash=refresh_token_hash,
            expires_at=refresh_expiry,
            device_info=device_info or {}
        )
        db.add(refresh_token_model)
        await db.commit()
        
        return access_token, refresh_token, access_expiry, refresh_expiry
    
    @staticmethod
    async def refresh_access_token(
        db: AsyncSession,
        refresh_token: str
    ) -> Optional[Tuple[str, datetime]]:
        """Exchange refresh token for new access token"""
        token_hash = hash_refresh_token(refresh_token)
        
        # Find valid refresh token
        result = await db.execute(
            select(RefreshToken).where(
                and_(
                    RefreshToken.token_hash == token_hash,
                    RefreshToken.expires_at > datetime.now(timezone.utc),
                    RefreshToken.revoked_at.is_(None)
                )
            )
        )
        refresh_token_model = result.scalar_one_or_none()
        
        if not refresh_token_model:
            return None
        
        # Update last used timestamp
        refresh_token_model.last_used_at = datetime.now(timezone.utc)
        await db.commit()
        
        # Create new access token
        access_token_data = {"sub": str(refresh_token_model.user_id)}
        access_token = create_access_token(access_token_data)
        access_expiry = datetime.now(timezone.utc) + timedelta(minutes=settings.computed_access_token_expire_minutes)
        
        return access_token, access_expiry
    
    @staticmethod
    async def revoke_refresh_token(db: AsyncSession, refresh_token: str) -> bool:
        """Revoke a refresh token"""
        token_hash = hash_refresh_token(refresh_token)
        
        result = await db.execute(
            select(RefreshToken).where(
                and_(
                    RefreshToken.token_hash == token_hash,
                    RefreshToken.revoked_at.is_(None)
                )
            )
        )
        refresh_token_model = result.scalar_one_or_none()
        
        if refresh_token_model:
            refresh_token_model.revoked_at = datetime.now(timezone.utc)
            await db.commit()
            return True
        
        return False
    
    @staticmethod
    async def revoke_all_user_tokens(db: AsyncSession, user_id: UUID):
        """Revoke all refresh tokens for a user"""
        result = await db.execute(
            select(RefreshToken).where(
                and_(
                    RefreshToken.user_id == user_id,
                    RefreshToken.revoked_at.is_(None)
                )
            )
        )
        tokens = result.scalars().all()
        
        for token in tokens:
            token.revoked_at = datetime.now(timezone.utc)
        
        await db.commit()
    
    @staticmethod
    async def get_user_by_jwt_token(db: AsyncSession, token: str) -> Optional[User]:
        """Get user by JWT access token"""
        payload = verify_access_token(token)
        if not payload:
            return None
        
        user_id = payload.get("sub")
        if not user_id:
            return None
        
        result = await db.execute(
            select(User).where(
                and_(
                    User.id == UUID(user_id),
                    User.deleted_at.is_(None)  # Exclude soft deleted users
                )
            )
        )
        return result.scalar_one_or_none()


def log_admin_action(
    db: AsyncSession,
    admin_id: UUID,
    action_type: str,
    target_id: Optional[UUID] = None,
    target_type: Optional[str] = None,
    action_data: Optional[Dict[str, Any]] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None
) -> None:
    """Log an admin action to the admin_actions table"""
    try:
        # Convert action_data to JSON string
        action_data_json = json.dumps(action_data) if action_data else '{}'
        
        # Insert into admin_actions table
        db.execute(
            text("""
                INSERT INTO admin_actions (
                    admin_id, action_type, target_id, target_type,
                    action_data, ip_address, user_agent, created_at
                ) VALUES (
                    :admin_id, :action_type, :target_id, :target_type,
                    :action_data::jsonb, :ip_address, :user_agent, CURRENT_TIMESTAMP
                )
            """),
            {
                "admin_id": admin_id,
                "action_type": action_type,
                "target_id": target_id,
                "target_type": target_type,
                "action_data": action_data_json,
                "ip_address": ip_address,
                "user_agent": user_agent
            }
        )
    except Exception as e:
        # Log error but don't fail the main operation
        print(f"Failed to log admin action: {e}")