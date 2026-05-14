"""
TICMI - Teach Me
FastAPI Backend Application with WebSocket Support for Streaming AI Agent Reasoning.

This is the main entry point for the TICMI backend service.
It sets up:
- FastAPI application with CORS
- WebSocket endpoint for real-time AI agent streaming
- REST API endpoints for session management
- Health check and status endpoints
"""

import asyncio
import json
from typing import Dict, Any, Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

from .core.config import settings
from .schemas.chat import ChatRequest, ChatResponse, ChatMessage, AgentStateSchema
from .ai_agents.graph import get_agent_graph, TicmiAgentGraph
from .ai_agents.state_manager import state_manager


# ============================================================================
# LIFESPAN MANAGER
# ============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager for startup and shutdown events.
    
    Handles:
    - Initializing AI agent graph on startup
    - Cleaning up resources on shutdown
    """
    # Startup
    print(f"🚀 Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    print(f"📊 Debug mode: {settings.DEBUG}")
    
    # Initialize the agent graph
    agent_graph = get_agent_graph()
    print("✅ LangGraph multi-agent system initialized")
    
    yield
    
    # Shutdown
    print("👋 Shutting down TICMI backend...")
    # Add cleanup logic here (close DB connections, etc.)


# ============================================================================
# FASTAPI APPLICATION
# ============================================================================

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Adaptive Digital Learning Platform for High School Mathematics",
    lifespan=lifespan,
)

# Configure CORS for frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # Next.js dev server
        "http://localhost:8080",  # Alternative frontend port
        "https://ticmi.app",      # Production domain
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class SessionCreateRequest(BaseModel):
    """Request to create a new learning session."""
    user_id: Optional[str] = None
    current_topic: Optional[str] = None


class SessionCreateResponse(BaseModel):
    """Response with created session details."""
    session_id: str
    message: str


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    version: str
    agents_initialized: bool


# ============================================================================
# REST API ENDPOINTS
# ============================================================================

@app.get("/", tags=["Root"])
async def root():
    """Root endpoint with welcome message."""
    return {
        "message": f"Welcome to {settings.APP_NAME}",
        "version": settings.APP_VERSION,
        "docs": "/docs"
    }


@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """
    Health check endpoint for monitoring and load balancers.
    
    Returns:
        Health status with version and agent initialization state
    """
    try:
        # Try to get the agent graph to verify it's initialized
        agent_graph = get_agent_graph()
        agents_initialized = agent_graph is not None
    except Exception:
        agents_initialized = False
    
    return HealthResponse(
        status="healthy",
        version=settings.APP_VERSION,
        agents_initialized=agents_initialized
    )


@app.post("/sessions", response_model=SessionCreateResponse, tags=["Sessions"])
async def create_session(request: SessionCreateRequest):
    """
    Create a new learning session.
    
    Args:
        request: Session creation request with optional user_id and topic
        
    Returns:
        Created session ID
    """
    session_id = state_manager.create_session(
        user_id=request.user_id,
        current_topic=request.current_topic
    )
    
    return SessionCreateResponse(
        session_id=session_id,
        message="Session created successfully"
    )


@app.get("/sessions/{session_id}/state", tags=["Sessions"])
async def get_session_state(session_id: str):
    """
    Get the current state of a learning session.
    
    Args:
        session_id: Session identifier
        
    Returns:
        Current session state including messages and agent state
    """
    state = state_manager.get_state(session_id)
    
    if state is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found"
        )
    
    # Convert to serializable format
    return {
        "session_id": session_id,
        "messages_count": len(state.get("messages", [])),
        "current_error_type": state.get("current_error_type"),
        "prerequisite_resolved": state.get("prerequisite_resolved", False),
        "user_competency_level": state.get("user_competency_level", "intermediate"),
        "socratic_turns": state.get("socratic_turns", 0),
    }


@app.delete("/sessions/{session_id}", tags=["Sessions"])
async def delete_session(session_id: str):
    """
    Delete a learning session.
    
    Args:
        session_id: Session identifier
    """
    success = state_manager.delete_session(session_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found"
        )
    
    return {"message": f"Session {session_id} deleted"}


# ============================================================================
# WEBSOCKET ENDPOINT FOR STREAMING
# ============================================================================

@app.websocket("/ws/chat/{session_id}")
async def websocket_chat_endpoint(websocket: WebSocket, session_id: str):
    """
    WebSocket endpoint for real-time streaming of AI agent reasoning.
    
    This endpoint:
    1. Accepts WebSocket connection
    2. Receives user messages
    3. Streams AI agent responses in real-time as they're generated
    4. Sends agent state updates for UI visualization
    
    Message Format (Client → Server):
    {
        "type": "message",
        "content": "User's message text",
        "topic": "Optional current topic"
    }
    
    Message Format (Server → Client):
    {
        "type": "stream_start" | "stream_chunk" | "stream_end" | "error" | "state_update",
        "content": "Message content or chunk",
        "node": "Current agent node name",
        "state": "Current agent state (optional)"
    }
    
    Args:
        websocket: WebSocket connection
        session_id: Unique session identifier from URL path
    """
    await websocket.accept()
    
    # Ensure session exists
    initial_state = state_manager.create_session(session_id=session_id)
    
    # Send connection confirmation
    await websocket.send_json({
        "type": "connection_established",
        "session_id": session_id,
        "message": "Connected to TICMI AI Tutor"
    })
    
    # Get the agent graph instance
    agent_graph: TicmiAgentGraph = get_agent_graph()
    
    try:
        while True:
            # Wait for client message
            data = await websocket.receive_text()
            
            try:
                message_data = json.loads(data)
            except json.JSONDecodeError:
                # Handle plain text messages
                message_data = {"type": "message", "content": data}
            
            if message_data.get("type") != "message":
                continue
            
            user_content = message_data.get("content", "")
            current_topic = message_data.get("topic")
            
            if not user_content:
                continue
            
            # Send acknowledgment that we're processing
            await websocket.send_json({
                "type": "processing",
                "message": "Analyzing your response..."
            })
            
            # Process through agent graph with streaming
            try:
                # Prepare the graph input
                from langchain_core.messages import HumanMessage
                
                graph_input = {
                    "messages": [HumanMessage(content=user_content)],
                    "current_error_type": None,
                    "prerequisite_resolved": False,
                    "user_competency_level": initial_state.get("user_competency_level", "intermediate"),
                    "session_id": session_id,
                    "current_topic": current_topic,
                    "diagnostic_complete": False,
                    "socratic_turns": 0,
                }
                
                # Stream the graph execution
                full_response = ""
                current_node = "unknown"
                
                async for event in agent_graph.graph.astream(
                    graph_input,
                    config={"configurable": {"session_id": session_id}},
                    stream_mode="updates"
                ):
                    # event is a dict: {node_name: output}
                    for node_name, node_output in event.items():
                        current_node = node_name
                        
                        # Send node execution update
                        await websocket.send_json({
                            "type": "node_update",
                            "node": node_name,
                            "timestamp": asyncio.get_event_loop().time()
                        })
                        
                        # Extract and stream any messages from the node output
                        if isinstance(node_output, dict):
                            messages = node_output.get("messages", [])
                            for msg in messages:
                                if hasattr(msg, 'content'):
                                    chunk = msg.content
                                    full_response += chunk
                                    
                                    # Stream the chunk
                                    await websocket.send_json({
                                        "type": "stream_chunk",
                                        "content": chunk,
                                        "node": node_name,
                                        "complete": False
                                    })
                
                # Send completion
                await websocket.send_json({
                    "type": "stream_end",
                    "content": full_response,
                    "node": current_node,
                    "complete": True
                })
                
                # Send final state update
                final_state = state_manager.get_state(session_id)
                if final_state:
                    await websocket.send_json({
                        "type": "state_update",
                        "state": {
                            "current_node": current_node,
                            "messages_count": len(final_state.get("messages", [])),
                            "current_error_type": final_state.get("current_error_type"),
                            "prerequisite_resolved": final_state.get("prerequisite_resolved", False),
                            "user_competency_level": final_state.get("user_competency_level", "intermediate"),
                        }
                    })
                
            except Exception as e:
                # Send error to client
                await websocket.send_json({
                    "type": "error",
                    "message": str(e),
                    "code": "agent_execution_error"
                })
                
    except WebSocketDisconnect:
        print(f"Client disconnected: {session_id}")
    except Exception as e:
        print(f"WebSocket error: {e}")
        try:
            await websocket.send_json({
                "type": "error",
                "message": "Internal server error",
                "code": "internal_error"
            })
        except Exception:
            pass
        finally:
            await websocket.close()


# ============================================================================
# SERVER ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    uvicorn.run(
        "backend.app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="info" if settings.DEBUG else "warning"
    )
