from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, Tuple
from jose import JWTError, jwt
from passlib.context import CryptContext
import secrets
import string
import hashlib

from .config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.computed_access_token_expire_minutes)
    
    to_encode.update({
        "exp": expire,
        "type": "access",
        "iat": datetime.now(timezone.utc)
    })
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def verify_token(token: str) -> Optional[Dict[str, Any]]:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError:
        return None

def generate_otp(length: int = 6) -> str:
    """Generate a numeric OTP of specified length"""
    return ''.join(secrets.choice(string.digits) for _ in range(length))

def generate_session_token() -> str:
    """Generate a secure random session token"""
    return secrets.token_urlsafe(32)

def generate_refresh_token() -> str:
    """Generate a secure random refresh token"""
    return secrets.token_urlsafe(64)

def hash_refresh_token(token: str) -> str:
    """Hash refresh token for secure storage"""
    return hashlib.sha256(token.encode()).hexdigest()

def create_token_pair(user_id: str) -> Tuple[str, str, datetime, datetime]:
    """Create access and refresh token pair
    Returns: (access_token, refresh_token, access_expiry, refresh_expiry)
    """
    # Create access token
    access_token_data = {"sub": user_id}
    access_token = create_access_token(access_token_data)
    access_expiry = datetime.now(timezone.utc) + timedelta(minutes=settings.computed_access_token_expire_minutes)
    
    # Create refresh token
    refresh_token = generate_refresh_token()
    refresh_expiry = datetime.now(timezone.utc) + timedelta(days=settings.computed_refresh_token_expire_days)
    
    return access_token, refresh_token, access_expiry, refresh_expiry

def verify_access_token(token: str) -> Optional[Dict[str, Any]]:
    """Verify access token and check token type"""
    payload = verify_token(token)
    if payload and payload.get("type") == "access":
        return payload
    return None