from fastapi import APIRouter, HTTPException, Depends, status, Response
from ..models.user import PhoneVerification, OTPVerification, UserLogin, UserCreate
from ..utils.otp import send_otp, verify_otp
from ..db.database import login_user_with_phone, refresh_access_token, revoke_refresh_token, get_user_by_phone, add_user
import uuid

router = APIRouter(
    prefix="/auth",
    tags=["authentication"],
    responses={404: {"description": "Not found"}}
)

@router.post("/send-otp")
async def send_verification_otp(phone: PhoneVerification):
    """Send OTP to the provided phone number"""
    success, message = send_otp(phone.phone_number)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=message
        )
        
    return {"message": message}

@router.post("/verify-otp")
async def verify_phone_otp(verification: OTPVerification, response: Response):
    """Verify OTP for the provided phone number and set auth token in cookie"""
    is_valid = verify_otp(verification.phone_number, verification.otp)
    
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired OTP"
        )
        
    # Check if user exists with this phone number
    user = get_user_by_phone(verification.phone_number)
    
    if not user:
        # Auto-create a new user account
        user_data = {
            "id": str(uuid.uuid4()),
            "phone": verification.phone_number,
            "name": f"User-{verification.phone_number[-4:]}",  # Default name based on last 4 digits
            "role": "customer",
            "is_active": True
        }
        
        # Add the new user to the database
        add_user(user_data)
    
    # Login the user (existing or newly created)
    login_result = login_user_with_phone(verification.phone_number)
    
    if not login_result:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate login tokens"
        )
    
    # Set access token in HTTP-only cookie
    response.set_cookie(
        key="access_token",
        value=login_result['access_token'],
        httponly=True,
        max_age=login_result['expires_in'],
        secure=False,  # Set to True in production with HTTPS
        samesite="lax"
    )
    
    # Set refresh token in a separate HTTP-only cookie
    response.set_cookie(
        key="refresh_token",
        value=login_result['refresh_token'],
        httponly=True,
        max_age=30 * 24 * 60 * 60,  # 30 days in seconds
        secure=False,  # Set to True in production with HTTPS
        samesite="lax"
    )
    
    # Return whether this was a new registration or existing user login
    return {
        "message": "Phone verification successful",
        "verified": True,
        "user_exists": user is not None,
        "user": login_result["user"]
    }

@router.post("/refresh-token")
async def refresh_token_endpoint(refresh_token: str):
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
async def logout(response: Response):
    """Logout a user by clearing auth cookies"""
    # Clear the auth cookies
    response.delete_cookie(key="access_token")
    response.delete_cookie(key="refresh_token")
    
    return {"message": "Successfully logged out"}

@router.post("/login")
async def login(credentials: UserLogin):
    """Send OTP to the provided phone number for login"""
    # First send OTP to the phone number
    success, message = send_otp(credentials.phone_number)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=message
        )
        
    return {"message": "OTP sent to your phone number", "phone_number": credentials.phone_number}
