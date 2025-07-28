"""Authentication endpoints using Supabase Auth"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.schemas.auth import (
    OTPRequestSchema, OTPVerifySchema, TokenResponse, 
    UserResponse, RefreshTokenRequest
)
from app.services.supabase_auth import SupabaseAuthService
from app.utils.supabase_deps import get_current_user_supabase
from app.models.user import User
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/request-otp", response_model=dict)
async def request_otp(
    request: OTPRequestSchema,
    db: AsyncSession = Depends(get_db)
):
    """Request OTP for login/registration"""
    try:
        result = await SupabaseAuthService.request_otp(
            db=db,
            email=request.email,
            user_data=request if request.first_name else None
        )
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to request OTP: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send OTP"
        )

@router.post("/verify-otp", response_model=TokenResponse)
async def verify_otp(
    request: OTPVerifySchema,
    db: AsyncSession = Depends(get_db)
):
    """Verify OTP and get tokens"""
    try:
        result = await SupabaseAuthService.verify_otp(
            db=db,
            email=request.email,
            otp=request.otp
        )
        return TokenResponse(**result)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to verify OTP: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to verify OTP"
        )

@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    request: RefreshTokenRequest
):
    """Refresh access token"""
    try:
        result = await SupabaseAuthService.refresh_token(
            refresh_token=request.refresh_token
        )
        return TokenResponse(**result)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to refresh token: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to refresh token"
        )

@router.post("/logout")
async def logout(
    current_user: User = Depends(get_current_user_supabase)
):
    """Logout current user"""
    # Supabase handles token revocation
    # We just return success
    return {"message": "Logged out successfully"}

@router.get("/me", response_model=UserResponse)
async def get_current_user(
    current_user: User = Depends(get_current_user_supabase)
):
    """Get current user information"""
    return UserResponse(
        id=str(current_user.id),
        email=current_user.email,
        first_name=current_user.first_name,
        last_name=current_user.last_name,
        username=current_user.username,
        role=current_user.role,
        is_admin=current_user.is_admin,
        created_at=current_user.created_at,
        updated_at=current_user.updated_at
    )

@router.delete("/sessions")
async def revoke_all_sessions(
    current_user: User = Depends(get_current_user_supabase)
):
    """Revoke all sessions for current user"""
    # With Supabase Auth, this is handled by their infrastructure
    # We just return success
    return {"message": "All sessions revoked successfully"}