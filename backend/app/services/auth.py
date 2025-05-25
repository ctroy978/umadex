from datetime import datetime, timedelta, timezone
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from uuid import UUID

from app.models import User, EmailWhitelist, OTPRequest, UserSession
from app.core.security import generate_otp, generate_session_token
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
                    UserSession.expires_at > datetime.now(timezone.utc)
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