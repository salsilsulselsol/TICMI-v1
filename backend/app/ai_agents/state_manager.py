"""
State Manager for LangGraph multi-agent workflow.
Handles session-specific state persistence and retrieval.
"""

from typing import Dict, Any, Optional
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
import uuid


class StateManager:
    """
    Manages conversation state for multiple sessions.
    
    In production, this would be backed by Redis or a database.
    For now, uses in-memory storage with session expiration.
    """
    
    def __init__(self):
        self._sessions: Dict[str, Dict[str, Any]] = {}
    
    def create_session(
        self, 
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
        current_topic: Optional[str] = None
    ) -> str:
        """
        Create a new session with initial state.
        
        Args:
            session_id: Optional custom session ID
            user_id: Optional user identifier
            current_topic: Current math topic being studied
            
        Returns:
            session_id: The created or existing session ID
        """
        if session_id is None:
            session_id = str(uuid.uuid4())
        
        if session_id not in self._sessions:
            self._sessions[session_id] = {
                "messages": [],
                "current_error_type": None,
                "prerequisite_resolved": False,
                "user_competency_level": "intermediate",
                "session_id": session_id,
                "user_id": user_id,
                "current_topic": current_topic,
                "diagnostic_complete": False,
                "socratic_turns": 0,
            }
        
        return session_id
    
    def get_state(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get the current state for a session."""
        return self._sessions.get(session_id)
    
    def update_state(
        self, 
        session_id: str, 
        updates: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Update specific fields in the session state.
        
        Args:
            session_id: Session identifier
            updates: Dictionary of fields to update
            
        Returns:
            Updated state dictionary
        """
        if session_id not in self._sessions:
            raise ValueError(f"Session {session_id} not found")
        
        state = self._sessions[session_id]
        
        # Special handling for messages - append instead of replace
        if "messages" in updates:
            new_messages = updates["messages"]
            if isinstance(new_messages, list):
                state["messages"].extend(new_messages)
            else:
                state["messages"].append(new_messages)
            updates.pop("messages")
        
        # Update other fields
        state.update(updates)
        
        return state
    
    def add_message(
        self, 
        session_id: str, 
        role: str, 
        content: str
    ) -> Dict[str, Any]:
        """
        Add a message to the conversation history.
        
        Args:
            session_id: Session identifier
            role: Message role ("user" or "assistant")
            content: Message content
            
        Returns:
            Updated state dictionary
        """
        if role == "user":
            message = HumanMessage(content=content)
        else:
            message = AIMessage(content=content)
        
        return self.update_state(session_id, {"messages": [message]})
    
    def get_messages(self, session_id: str) -> list[BaseMessage]:
        """Get all messages for a session."""
        state = self.get_state(session_id)
        if state is None:
            return []
        return state.get("messages", [])
    
    def reset_session(self, session_id: str) -> bool:
        """
        Reset a session to initial state (for starting new topics).
        
        Args:
            session_id: Session identifier
            
        Returns:
            True if session was reset, False if not found
        """
        if session_id not in self._sessions:
            return False
        
        state = self._sessions[session_id]
        state.update({
            "messages": [],
            "current_error_type": None,
            "prerequisite_resolved": False,
            "diagnostic_complete": False,
            "socratic_turns": 0,
        })
        
        return True
    
    def delete_session(self, session_id: str) -> bool:
        """Delete a session."""
        if session_id in self._sessions:
            del self._sessions[session_id]
            return True
        return False


# Global state manager instance
state_manager = StateManager()
