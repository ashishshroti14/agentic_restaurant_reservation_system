from pydantic import BaseModel, Field
from typing import List, Optional, Literal
from datetime import datetime
from uuid import uuid4

class ChatMessage(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    role: Literal["user", "assistant", "system"] = "user"
    content: str
    timestamp: datetime = Field(default_factory=datetime.now)
    
class ChatSession(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    user_id: Optional[str] = None
    phone_number: Optional[str] = None  # Add phone number field
    messages: List[ChatMessage] = []
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    
class ChatRequest(BaseModel):
    session_id: Optional[str] = None
    message: str
    restaurant_id: Optional[str] = None
    
class ChatResponse(BaseModel):
    session_id: str
    message: ChatMessage
    suggested_actions: Optional[List[str]] = None
    intent: str
