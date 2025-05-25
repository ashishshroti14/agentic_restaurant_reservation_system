from fastapi import APIRouter, HTTPException, Depends, status, Header
from fastapi.security import OAuth2PasswordBearer
from typing import List, Optional
from ..models.user import User, UserCreate, UserUpdate, PhoneVerification, OTPVerification, UserLogin
from ..db.database import (
    add_user, 
    get_user, 
    get_users, 
    update_user, 
    delete_user,
    refresh_access_token,
    revoke_refresh_token
)
from ..utils.otp import send_otp
from ..utils.auth import get_current_user, verify_admin
import uuid

router = APIRouter(
    prefix="/users",
    tags=["users"],
    responses={404: {"description": "Not found"}},
)

@router.post("/register", response_model=User)
def register_user(user: UserCreate):
    """Register a new user"""
    # Check if phone number already exists
    existing_user = get_user_by_phone(user.phone_number)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Phone number already registered"
        )
        
    user_dict = user.dict()
    user_dict["id"] = str(uuid.uuid4())
    user_dict["phone"] = user_dict.pop("phone_number")  # Convert to phone field in DB
    
    result = add_user(user_dict)
    
    if isinstance(result, dict) and "error" in result:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result["error"]
        )
        
    return result

@router.post("/login")
def login(credentials: UserLogin):
    """Authenticate a user and return JWT tokens"""
    # We'll delegate to the auth router for sending OTP
    success, message = send_otp(credentials.phone_number)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=message
        )
    
    return {"message": f"OTP sent to {credentials.phone_number}"}

@router.post("/refresh-token")
def refresh_token_endpoint(refresh_token: str):
    """Get a new access token using a refresh token"""
    new_access_token = refresh_access_token(refresh_token)
    if not new_access_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token"
        )
    
    return {
        "access_token": new_access_token,
        "token_type": "bearer"
    }

@router.post("/logout")
def logout(refresh_token: str):
    """Logout a user by revoking their refresh token"""
    revoked = revoke_refresh_token(refresh_token)
    if not revoked:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid token"
        )
    
    return {"message": "Successfully logged out"}

# Protected endpoint - only admins can see all users
@router.get("/", response_model=List[User])
def get_all_users(
    role: str = None,
    current_user: dict = Depends(verify_admin)
):
    """Get all users, optionally filtered by role (Admin only)"""
    return get_users(role=role)

# Protected endpoint - users can see their own profile or admins can see any profile
@router.get("/{user_id}", response_model=User)
def get_user_by_id(
    user_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get a specific user by ID"""
    # Check if the user is requesting their own profile or if they are an admin
    if current_user["id"] != user_id and current_user["role"] != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. You can only view your own profile."
        )
    
    user = get_user(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return user

# Protected endpoint - users can update their own profile or admins can update any profile
@router.put("/{user_id}", response_model=User)
def update_user_profile(
    user_id: str,
    user_data: UserUpdate,
    current_user: dict = Depends(get_current_user)
):
    """Update a user's profile"""
    # Check if the user is updating their own profile or if they are an admin
    if current_user["id"] != user_id and current_user["role"] != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. You can only update your own profile."
        )
    
    updated_data = {k: v for k, v in user_data.dict().items() if v is not None}
    
    # Prevent role changes unless the user is an admin
    if "role" in updated_data and current_user["role"] != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can change user roles."
        )
    
    result = update_user(user_id, updated_data)
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    if isinstance(result, dict) and "error" in result:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result["error"]
        )
        
    return result

# Protected endpoint - users can delete their own account or admins can delete any account
@router.delete("/{user_id}")
def delete_user_account(
    user_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Delete a user account"""
    # Check if the user is deleting their own account or if they are an admin
    if current_user["id"] != user_id and current_user["role"] != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. You can only delete your own account."
        )
    
    success = delete_user(user_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return {"message": "User deleted successfully"}

# Get current user's profile
@router.get("/me/profile", response_model=User)
def get_current_user_profile(current_user: dict = Depends(get_current_user)):
    """Get the current authenticated user's profile"""
    return current_user
