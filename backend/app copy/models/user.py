from pydantic import BaseModel, Field, EmailStr, validator
from typing import Optional
import re
from datetime import datetime

class UserBase(BaseModel):
    phone_number: str
    name: Optional[str] = None
    
    @validator('phone_number')
    def phone_number_must_be_valid(cls, v):
        # Simple validation - adapt to your needs
        if not re.match(r'^\+?[1-9]\d{1,14}$', v):
            raise ValueError('Invalid phone number format')
        return v

class UserCreate(UserBase):
    pass

class UserResponse(UserBase):
    id: str
    is_active: bool

    class Config:
        orm_mode = True

class UserInDB(UserBase):
    id: str
    is_active: bool = True
    created_at: str
    updated_at: str

    class Config:
        orm_mode = True

class UserUpdate(BaseModel):
    name: Optional[str] = None
    phone_number: Optional[str] = None
    role: Optional[str] = None

class User(BaseModel):
    id: str
    role: str
    created_at: Optional[str] = None

    class Config:
        orm_mode = True
        
class UserLogin(BaseModel):
    phone_number: str = Field(..., description="Phone number with country code (e.g., +1234567890)")

class PhoneVerification(BaseModel):
    phone_number: str = Field(..., description="Phone number with country code (e.g., +1234567890)")

class OTPVerification(BaseModel):
    phone_number: str = Field(..., description="Phone number with country code")
    otp: str = Field(..., description="OTP code received via SMS")
