from pydantic import BaseModel, EmailStr
from typing import Optional

class Restaurant(BaseModel):
    id: str
    name: str
    location: str
    cuisine: str
    total_capacity: int
    opening_time: str
    closing_time: str
    description: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    # New contact details
    email: Optional[str] = None
    phone: Optional[str] = None
    website: Optional[str] = None
    address: Optional[str] = None
