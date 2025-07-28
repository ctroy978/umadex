from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone

from app.core.database import get_db
from app.schemas.auth import (
    OTPRequestSchema, OTPVerifySchema, TokenResponse, UserResponse,
    RefreshTokenRequest, RefreshTokenResponse
)
from app.schemas.user import UserCreate
from app.services.auth import AuthService
from app.services.email import EmailService
from app.services.user import UserService
from app.utils.supabase_deps import get_current_user_supabase as get_current_user
from app.models import User

router = APIRouter()

@router.post("/request-otp", status_code=status.HTTP_200_OK)
async def request_otp(
    request: OTPRequestSchema,
    db: AsyncSession = Depends(get_db)
):
    """Request OTP for login or registration"""
    # Check if email is whitelisted
    if not await AuthService.check_email_whitelist(db, request.email):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email not authorized for registration"
        )
    
    # Check if user exists
    user = await UserService.get_user_by_email(db, request.email)
    
    # If user doesn't exist and registration data provided, validate it
    if not user and (not request.first_name or not request.last_name):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="First name and last name required for new users"
        )
    
    # If new user with registration data, create the user
    if not user and request.first_name and request.last_name:
        user_create = UserCreate(
            email=request.email,
            first_name=request.first_name,
            last_name=request.last_name
        )
        user = await UserService.create_user(db, user_create)
    
    # Generate and send OTP
    otp = await AuthService.generate_and_store_otp(request.email)
    await EmailService.send_otp_email(request.email, otp)
    
    return {
        "message": "OTP sent to your email",
        "is_new_user": user is None or (request.first_name and request.last_name)
    }

@router.post("/verify-otp", response_model=TokenResponse)
async def verify_otp(
    request: OTPVerifySchema,
    db: AsyncSession = Depends(get_db)
):
    """Verify OTP and create session with JWT tokens"""
    # Verify OTP
    if not await AuthService.verify_otp(request.email, request.otp_code):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired OTP"
        )
    
    # Get or create user
    user = await UserService.get_user_by_email(db, request.email)
    
    if not user:
        # This shouldn't happen if frontend flow is followed correctly
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User registration required. Please request OTP with registration details."
        )
    
    # Create JWT token pair
    access_token, refresh_token, access_expiry, refresh_expiry = await AuthService.create_token_pair_for_user(
        db, user.id
    )
    
    # Calculate expires_in (seconds)
    expires_in = int((access_expiry - datetime.now(timezone.utc)).total_seconds())
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=expires_in,
        user=UserResponse.model_validate(user)
    )

@router.post("/refresh", response_model=RefreshTokenResponse)
async def refresh_token(
    request: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db)
):
    """Exchange refresh token for new access token"""
    result = await AuthService.refresh_access_token(db, request.refresh_token)
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token"
        )
    
    access_token, access_expiry = result
    expires_in = int((access_expiry - datetime.now(timezone.utc)).total_seconds())
    
    return RefreshTokenResponse(
        access_token=access_token,
        expires_in=expires_in
    )

@router.post("/logout", status_code=status.HTTP_200_OK)
async def logout(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Logout current user and revoke refresh token if provided"""
    # Try to get refresh token from request body
    try:
        body = await request.json()
        refresh_token = body.get("refresh_token")
        if refresh_token:
            await AuthService.revoke_refresh_token(db, refresh_token)
    except:
        pass  # No body or invalid JSON, that's OK
    
    return {"message": "Logged out successfully"}

@router.delete("/sessions", status_code=status.HTTP_200_OK)
async def revoke_all_sessions(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Revoke all refresh tokens for the current user"""
    await AuthService.revoke_all_user_tokens(db, current_user.id)
    return {"message": "All sessions revoked successfully"}

@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    """Get current user information"""
    return UserResponse.model_validate(current_user)