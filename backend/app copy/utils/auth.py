from fastapi import Depends, Cookie, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from typing import Optional
from ..db.database import verify_token

# Standard OAuth2 scheme (for Swagger UI support)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/verify-otp")

async def get_token_from_cookie_or_header(
    request: Request,
    access_token: Optional[str] = Cookie(None),
) -> str:
    """
    Get the access token from either a cookie or the Authorization header.
    This provides flexibility for different client types.
    """
    # First try to get token from cookie
    if access_token:
        # If token starts with "Bearer ", remove it
        if access_token.startswith("Bearer "):
            return access_token[7:]
        return access_token
    
    # If no cookie token, try Authorization header
    authorization = request.headers.get("Authorization")
    if authorization and authorization.startswith("Bearer "):
        return authorization[7:]  # Remove "Bearer " prefix
    
    # No token found
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated. Missing access token in cookie or Authorization header.",
        headers={"WWW-Authenticate": "Bearer"},
    )

async def get_current_user(token: str = Depends(get_token_from_cookie_or_header)):
    """Dependency to get the current authenticated user from the JWT token"""
    user = verify_token(token)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user

async def verify_admin(current_user: dict = Depends(get_current_user)):
    """Verify that the current user is an admin"""
    if current_user["role"] != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Operation not permitted. Admin access required."
        )
    return current_user
