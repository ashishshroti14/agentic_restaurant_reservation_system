from fastapi import APIRouter, HTTPException, Depends, status
from typing import List, Optional
from ..models.chat import ChatRequest, ChatResponse, ChatSession
from ..utils.chat_agent import process_user_message, get_or_create_session
from ..utils.auth import get_current_user  # Updated import

router = APIRouter(
    prefix="/chat",
    tags=["chat"],
    responses={404: {"description": "Not found"}}
)

@router.post("/message", response_model=ChatResponse)
async def send_message(
    request: ChatRequest,
    current_user: Optional[dict] = Depends(get_current_user)
):
    """Send a message to the chat agent and get a response"""
    user_id = current_user.get("id") if current_user else None
    phone_number = current_user.get("phone") if current_user else None
    
    session, assistant_msg, suggested_actions, intent = process_user_message(
        session_id=request.session_id,
        user_message=request.message,
        user_id=user_id,
        restaurant_id=request.restaurant_id,
        phone_number=phone_number
    )
    
    return ChatResponse(
        session_id=session.id,
        message=assistant_msg,
        suggested_actions=suggested_actions,
        intent=intent
    )

@router.get("/sessions/{session_id}", response_model=ChatSession)
async def get_chat_session(
    session_id: str,
    current_user: Optional[dict] = Depends(get_current_user)
):
    """Get a chat session by ID"""
    session = get_or_create_session(session_id)
    
    # Check if user has access to this session
    if current_user and session.user_id and session.user_id != current_user.get("id"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. This chat session belongs to another user."
        )
    
    return session
