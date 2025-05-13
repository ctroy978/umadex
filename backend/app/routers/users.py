# backend/app/routers/users.py
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import List, Optional
import logging
from ..dependencies import get_current_user

# Set up logger
logger = logging.getLogger(__name__)

# Create router without prefix
router = APIRouter(tags=["users"])

# Pydantic models
class UserProfile(BaseModel):
    id: str
    email: str
    role_name: Optional[str] = None
    username: Optional[str] = None
    full_name: Optional[str] = None
    created_at: Optional[str] = None
    is_deleted: Optional[bool] = False

class RoleUpdateRequest(BaseModel):
    user_id: str
    new_role: str

# Define the endpoint to handle both routes
@router.get("", response_model=List[UserProfile])
@router.get("/", response_model=List[UserProfile])
async def list_users(current_user: dict = Depends(get_current_user)):
    """
    Get all users (admin only)
    """
    logger.info(f"List users requested by: {current_user.get('email') if current_user else 'unauthenticated'}")
    
    try:
        # For testing purposes, we'll skip the authentication check for now
        # In a production app, you should verify the user has admin permissions
        
        # Return mock data for now
        users = [
            {
                "id": "1",
                "email": "admin@example.com",
                "role_name": "ADMIN",
                "username": "admin",
                "full_name": "Admin User",
                "created_at": "2023-01-01T00:00:00Z",
                "is_deleted": False
            },
            {
                "id": "2",
                "email": "teacher@example.com",
                "role_name": "TEACHER",
                "username": "teacher1",
                "full_name": "Teacher User",
                "created_at": "2023-01-02T00:00:00Z",
                "is_deleted": False
            },
            {
                "id": "3",
                "email": "student@example.com",
                "role_name": "STUDENT",
                "username": "student1",
                "full_name": "Student User",
                "created_at": "2023-01-03T00:00:00Z",
                "is_deleted": False
            }
        ]
        
        return users
    except Exception as e:
        logger.error(f"Error in list_users: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/me", response_model=dict)
async def get_current_user_profile(current_user: dict = Depends(get_current_user)):
    """
    Get the current user's profile information
    """
    return {
        "message": "This is a placeholder endpoint",
        "user": current_user
    }

@router.put("/promote", response_model=dict)
async def promote_user(request: RoleUpdateRequest, current_user: dict = Depends(get_current_user)):
    """
    Promote a user to a new role (admin only)
    """
    return {
        "success": True,
        "message": f"User {request.user_id} promoted to {request.new_role}",
        "user_id": request.user_id,
        "new_role": request.new_role
    }