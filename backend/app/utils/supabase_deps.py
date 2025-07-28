"""Supabase authentication dependencies"""
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.models.user import User
from app.services.supabase_auth import SupabaseAuthService
import logging

logger = logging.getLogger(__name__)

# Use HTTPBearer for JWT token extraction
security = HTTPBearer(auto_error=False)

async def get_current_user_supabase(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> User:
    """Get current user from Supabase JWT token"""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token = credentials.credentials
    
    # Get user from token
    user = await SupabaseAuthService.get_user_from_token(db, token)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Set RLS context for Supabase
    from sqlalchemy import text
    await db.execute(text(f"SET LOCAL app.current_user_id = '{user.id}'"))
    
    return user

async def get_current_user_optional_supabase(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> Optional[User]:
    """Get current user if authenticated, otherwise None"""
    if not credentials:
        return None
    
    try:
        return await get_current_user_supabase(credentials, db)
    except HTTPException:
        return None

async def require_admin_supabase(
    current_user: User = Depends(get_current_user_supabase)
) -> User:
    """Require current user to be admin"""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user

async def require_teacher_supabase(
    current_user: User = Depends(get_current_user_supabase)
) -> User:
    """Require current user to be teacher or admin"""
    if current_user.role != "teacher" and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Teacher access required"
        )
    return current_user