"""
Chat-related Pydantic schemas for WebSocket communication.
"""

from pydantic import BaseModel, Field
from typing import Literal, Optional
from datetime import datetime


class ChatMessage(BaseModel):
    """Represents a single chat message."""
    
    role: Literal["user", "assistant", "system"] = Field(
        ..., 
        description="Role of the message sender"
    )
    content: str = Field(..., description="Message content")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Message timestamp"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "role": "user",
                "content": "How do I solve 2x + 5 = 15?",
                "timestamp": "2024-01-15T10:30:00Z"
            }
        }


class ChatRequest(BaseModel):
    """Request schema for chat interactions."""
    
    session_id: str = Field(..., description="Unique session identifier")
    user_id: Optional[str] = Field(None, description="Optional user ID")
    message: str = Field(..., description="User's input message")
    current_topic: Optional[str] = Field(
        None, 
        description="Current math topic being studied"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "sess_123abc",
                "user_id": "user_456",
                "message": "I got x = 5 but I'm not sure if it's correct",
                "current_topic": "linear_equations"
            }
        }


class ChatResponse(BaseModel):
    """Response schema for chat interactions with streaming support."""
    
    session_id: str = Field(..., description="Session identifier")
    message: ChatMessage = Field(..., description="AI response message")
    is_streaming: bool = Field(
        default=False, 
        description="Whether this is a streaming chunk"
    )
    stream_complete: bool = Field(
        default=False, 
        description="Whether streaming is complete"
    )
    agent_state: Optional[dict] = Field(
        None, 
        description="Current state of the agent graph"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "sess_123abc",
                "message": {
                    "role": "assistant",
                    "content": "Let me help you verify that solution...",
                    "timestamp": "2024-01-15T10:30:01Z"
                },
                "is_streaming": False,
                "stream_complete": True
            }
        }


class AgentStateSchema(BaseModel):
    """Schema for serializing agent state to frontend."""
    
    current_node: str = Field(..., description="Current node in the graph")
    messages_count: int = Field(..., description="Number of messages in conversation")
    current_error_type: Optional[str] = Field(
        None, 
        description="Type of error detected"
    )
    prerequisite_resolved: bool = Field(
        default=False, 
        description="Whether prerequisite gap has been resolved"
    )
    user_competency_level: Literal["beginner", "intermediate", "advanced"] = Field(
        default="intermediate",
        description="Assessed competency level of the user"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "current_node": "socratic_agent",
                "messages_count": 5,
                "current_error_type": "algebraic_manipulation",
                "prerequisite_resolved": False,
                "user_competency_level": "intermediate"
            }
        }
