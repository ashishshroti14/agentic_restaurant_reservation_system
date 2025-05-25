from fastapi import APIRouter, HTTPException, Depends, status
from ..models.user import PhoneVerification, OTPVerification, UserLogin
from ..db.database import refresh_access_token, revoke_refresh_token, get_user_by_phone
from ..utils.otp import send_otp, verify_otp

router = APIRouter(
    prefix="/auth",
    tags=["authentication"],
    responses={404: {"description": "Not found"}},
)

@router.post("/login")
def login(credentials: UserLogin):
    """Start authentication with phone number"""
    success, message = send_otp(credentials.phone_number)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=message
        )
    
    return {"message": message, "phone_number": credentials.phone_number}

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

@router.post("/send-otp")
def send_verification_otp(phone_data: PhoneVerification):
    """Send OTP to the provided phone number"""
    success, message = send_otp(phone_data.phone)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=message
        )
    
    return {"message": message}

@router.post("/verify-otp")
def verify_phone_otp(verification_data: OTPVerification):
    """Verify OTP for the provided phone number"""
    is_valid = verify_otp(verification_data.phone, verification_data.otp)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired OTP"
        )
    
    return {"message": "Phone number verified successfully"}
