from pydantic import BaseModel, Field, validator
import re

class PhoneNumber(BaseModel):
    phone_number: str = Field(..., description="Phone number with country code (e.g., +1234567890)")
    
    @validator('phone_number')
    def validate_phone_number(cls, v):
        # Simple validation for E.164 format (starts with + and has digits)
        pattern = re.compile(r'^\+\d{1,15}$')
        if not pattern.match(v):
            raise ValueError('Phone number must be in E.164 format (e.g., +1234567890)')
        return v

class OTPVerification(BaseModel):
    phone_number: str = Field(..., description="Phone number with country code")
    otp: str = Field(..., description="OTP code received via SMS")
    
    @validator('phone_number')
    def validate_phone_number(cls, v):
        # Simple validation for E.164 format
        pattern = re.compile(r'^\+\d{1,15}$')
        if not pattern.match(v):
            raise ValueError('Phone number must be in E.164 format (e.g., +1234567890)')
        return v
    
    @validator('otp')
    def validate_otp(cls, v):
        # Validate OTP is numeric and has correct length
        if not v.isdigit() or len(v) != 6:
            raise ValueError('OTP must be a 6-digit number')
        return v
