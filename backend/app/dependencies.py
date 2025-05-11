# backend/app/dependencies.py
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import os
import jwt
from jwt.exceptions import PyJWTError

# Setup Supabase client constants
supabase_url = os.environ.get("SUPABASE_URL", "")
supabase_key = os.environ.get("SUPABASE_SERVICE_KEY", "")  # Use service key for admin operations
supabase_anon_key = os.environ.get("SUPABASE_ANON_KEY", "")  # Use anon key for client-side operations

# Don't throw an error immediately - just log a warning
if not supabase_url or not supabase_key:
    print("WARNING: Missing Supabase environment variables. Some functionality will be limited.")

# HTTP Bearer token security scheme
security = HTTPBearer()

def get_supabase_client(jwt_token=None):
    """
    Return a Supabase client - placeholder for now
    """
    # Just return a mock object since we're not fully implementing this yet
    return {"client": "placeholder"}

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """
    Validate JWT token and return user info
    """
    token = credentials.credentials
    
    try:
        # Decode the token (simplified - in production you'd verify with JWK)
        payload = jwt.decode(token, options={"verify_signature": False})
        
        # Check if token is valid
        if not payload or not payload.get("sub"):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
            )
            
        # Return user information from token
        user_id = payload.get("sub")
        email = payload.get("email")
        
        return {
            "id": user_id,
            "email": email,
            "access_token": token
        }
            
    except PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
        )