from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from ..utils.chat_agent import process_user_message
from ..models.chat import ChatMessage

router = APIRouter()

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    user_id: Optional[str] = None
    restaurant_id: Optional[str] = None

class ChatResponse(BaseModel):
    session_id: str
    response: str
    suggested_actions: Optional[List[str]] = None
    agent: str

@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    try:
        # Process the user message
        session, assistant_msg, suggested_actions, agent = process_user_message(
            session_id=request.session_id,
            user_message=request.message,
            user_id=request.user_id,
            restaurant_id=request.restaurant_id
        )
        
        # Return the response
        return ChatResponse(
            session_id=session.id,
            response=assistant_msg.content,
            suggested_actions=suggested_actions,
            agent=agent
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing message: {str(e)}")
