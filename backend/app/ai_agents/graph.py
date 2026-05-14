"""
LangGraph Multi-Agent Workflow for TICMI.

This module defines the complete StateGraph for the adaptive learning system,
implementing a Centralized Supervisor/Router Pattern with:
- Diagnostic Agent (Supervisor): Analyzes input and routes conversation
- Socratic Verification Agent (Worker): Asks probing questions using Protege Effect
- Deterministic & LLM-based routing decisions

The graph is modeled as a directed graph where:
- Nodes: Python functions representing agents
- Edges: Define routing logic (both conditional and deterministic)
- State: Shared TypedDict that all nodes read from and write to
"""

from typing import Dict, Any, Literal, TypedDict, Annotated
from langgraph.graph import StateGraph, END
from langchain_core.messages import BaseMessage, add_messages
import asyncio

from .nodes import (
    entry_node,
    diagnostic_agent_node,
    socratic_agent_node,
    resolution_check_node,
)
from .state_manager import state_manager


# ============================================================================
# STATE SCHEMA
# ============================================================================

class AgentGraphState(TypedDict):
    """
    Core state schema for the LangGraph multi-agent workflow.
    
    This TypedDict defines the shared state that flows through all nodes.
    Each node reads from and writes to this state.
    
    Attributes:
        messages: Annotated list of conversation messages (accumulates via add_messages)
        current_error_type: Classification of detected math error
        prerequisite_resolved: Boolean flag indicating if knowledge gap is addressed
        user_competency_level: Assessment level (beginner/intermediate/advanced)
        session_id: Unique session identifier
        current_topic: Current mathematics topic being studied
        diagnostic_complete: Flag indicating diagnostic phase completion
        socratic_turns: Counter for socratic questioning rounds
    """
    messages: Annotated[list[BaseMessage], add_messages]
    current_error_type: str | None
    prerequisite_resolved: bool
    user_competency_level: Literal["beginner", "intermediate", "advanced"]
    session_id: str
    current_topic: str | None
    diagnostic_complete: bool
    socratic_turns: int


# ============================================================================
# ROUTING FUNCTIONS
# ============================================================================

def route_after_diagnostic(state: AgentGraphState) -> Literal["socratic_agent", "end"]:
    """
    Conditional edge router after diagnostic agent.
    
    Determines next node based on diagnostic results:
    - If prerequisite gap detected → route to socratic_agent
    - If no significant error → end the graph
    
    Args:
        state: Current graph state
        
    Returns:
        Node name or END token
    """
    # Check if diagnostic found a prerequisite gap
    error_type = state.get("current_error_type")
    
    # Route to socratic agent if error detected
    if error_type:
        return "socratic_agent"
    
    # No error detected, end the graph
    return "end"


def route_after_socratic(state: AgentGraphState) -> Literal["diagnostic_agent", "end"]:
    """
    Conditional edge router after socratic agent.
    
    Determines if we should:
    - Continue socratic dialogue (loop back to diagnostic for new student response)
    - End the remediation and return to main lesson
    
    This uses DETERMINISTIC routing based on the prerequisite_resolved flag.
    
    Args:
        state: Current graph state
        
    Returns:
        Node name or END token
    """
    # CRITICAL: Deterministic routing based on state flag
    # When prerequisite_resolved == True, exit the remediation loop
    if state.get("prerequisite_resolved", False):
        return "end"
    
    # Check if we've exceeded max socratic turns
    if state.get("socratic_turns", 0) >= 5:
        return "end"
    
    # Continue the socratic dialogue
    # In a real implementation, this would wait for student response
    # For now, we end and let the API layer handle the next user message
    return "end"


def should_continue(state: AgentGraphState) -> Literal["diagnostic_agent", "end"]:
    """
    Entry point router - decides if we should process the message.
    
    Args:
        state: Current graph state
        
    Returns:
        Node name or END token
    """
    messages = state.get("messages", [])
    
    # Don't process if no messages
    if not messages:
        return "end"
    
    # Process with diagnostic agent
    return "diagnostic_agent"


# ============================================================================
# GRAPH CONSTRUCTION
# ============================================================================

def create_agent_graph() -> StateGraph:
    """
    Create and configure the LangGraph StateGraph.
    
    This function:
    1. Initializes the StateGraph with our typed state schema
    2. Adds all agent nodes (entry, diagnostic, socratic, resolution)
    3. Configures conditional edges for dynamic routing
    4. Sets up deterministic transitions for known paths
    
    Returns:
        Compiled StateGraph ready for execution
    """
    
    # Initialize the graph with typed state
    # The StateGraph enforces type safety for all state operations
    workflow = StateGraph(AgentGraphState)
    
    # -------------------------------------------------------------------------
    # ADD NODES
    # Each node is a function that takes state and returns state updates
    # -------------------------------------------------------------------------
    
    # Entry node: Initialize conversation flow
    workflow.add_node("entry", entry_node)
    
    # Diagnostic Agent (Supervisor/Router): 
    # Parses input, classifies errors, determines routing
    workflow.add_node("diagnostic_agent", diagnostic_agent_node)
    
    # Socratic Verification Agent (Worker):
    # Asks probing questions using Protege Effect, NEVER gives direct answers
    workflow.add_node("socratic_agent", socratic_agent_node)
    
    # Resolution Check: Evaluates if knowledge gap is resolved
    workflow.add_node("resolution_check", resolution_check_node)
    
    # -------------------------------------------------------------------------
    # SET ENTRY POINT
    # All graph executions start at the entry node
    # -------------------------------------------------------------------------
    workflow.set_entry_point("entry")
    
    # -------------------------------------------------------------------------
    # ADD EDGES
    # Mix of deterministic and conditional routing
    # -------------------------------------------------------------------------
    
    # Entry → Diagnostic (deterministic)
    workflow.add_edge("entry", "diagnostic_agent")
    
    # Diagnostic → Socratic OR End (conditional based on error detection)
    workflow.add_conditional_edges(
        source="diagnostic_agent",
        condition=route_after_diagnostic,
        # Explicit mapping of possible routes for clarity
        path_map={
            "socratic_agent": "Continue to Socratic remediation",
            "end": "No error detected, end graph"
        }
    )
    
    # Socratic → Resolution Check (deterministic)
    workflow.add_edge("socratic_agent", "resolution_check")
    
    # Resolution Check → End OR back to Diagnostic (conditional)
    # If prerequisite_resolved == True → End (return to main lesson)
    # If still unresolved → Could loop back for more socratic questioning
    workflow.add_conditional_edges(
        source="resolution_check",
        condition=route_after_socratic,
        path_map={
            "diagnostic_agent": "Continue remediation cycle",
            "end": "Prerequisite resolved, return to main lesson"
        }
    )
    
    # -------------------------------------------------------------------------
    # COMPILE THE GRAPH
    # Creates an executable instance with interrupt points for streaming
    # -------------------------------------------------------------------------
    
    app = workflow.compile()
    
    return app


# ============================================================================
# GRAPH EXECUTION WRAPPER
# ============================================================================

class TicmiAgentGraph:
    """
    High-level wrapper for the LangGraph agent workflow.
    
    Provides a clean interface for:
    - Starting new sessions
    - Processing user messages
    - Streaming agent responses
    - Managing conversation state
    """
    
    def __init__(self):
        self._graph = create_agent_graph()
    
    @property
    def graph(self):
        """Get the compiled graph instance."""
        return self._graph
    
    async def process_message(
        self,
        session_id: str,
        user_message: str,
        current_topic: str | None = None,
        user_id: str | None = None,
    ) -> Dict[str, Any]:
        """
        Process a user message through the agent graph.
        
        Args:
            session_id: Unique session identifier
            user_message: The user's input message
            current_topic: Current math topic (optional)
            user_id: User identifier (optional)
            
        Returns:
            Dictionary containing:
                - response: AI response message
                - state: Updated graph state
                - routing_info: Information about graph traversal
        """
        # Initialize or get session state
        initial_state = state_manager.create_session(
            session_id=session_id,
            user_id=user_id,
            current_topic=current_topic
        )
        
        # Add user message to state
        from langchain_core.messages import HumanMessage
        user_msg = HumanMessage(content=user_message)
        
        # Prepare initial state for graph execution
        graph_input: AgentGraphState = {
            "messages": [user_msg],
            "current_error_type": None,
            "prerequisite_resolved": False,
            "user_competency_level": initial_state.get("user_competency_level", "intermediate"),
            "session_id": session_id,
            "current_topic": current_topic,
            "diagnostic_complete": False,
            "socratic_turns": 0,
        }
        
        # Execute the graph
        # stream_mode="values" yields the full state after each node
        # stream_mode="updates" yields only state changes
        final_state = None
        
        async for event in self._graph.astream(
            graph_input,
            config={"configurable": {"session_id": session_id}},
            stream_mode="values"
        ):
            final_state = event
            
            # Here you could yield streaming updates to the client
            # For WebSocket streaming, see the API layer
        
        # Update persistent state manager
        if final_state:
            state_manager.update_state(session_id, {
                "messages": final_state.get("messages", []),
                "current_error_type": final_state.get("current_error_type"),
                "prerequisite_resolved": final_state.get("prerequisite_resolved", False),
                "socratic_turns": final_state.get("socratic_turns", 0),
            })
        
        # Extract the last AI response
        messages = final_state.get("messages", []) if final_state else []
        ai_responses = [m for m in messages if hasattr(m, 'type') and m.type == 'ai']
        last_response = ai_responses[-1].content if ai_responses else ""
        
        return {
            "response": last_response,
            "state": final_state,
            "routing_info": {
                "error_type": final_state.get("current_error_type") if final_state else None,
                "prerequisite_resolved": final_state.get("prerequisite_resolved", False) if final_state else False,
                "socratic_turns": final_state.get("socratic_turns", 0) if final_state else 0,
            }
        }
    
    def get_state(self, session_id: str) -> Dict[str, Any] | None:
        """Get current state for a session."""
        return state_manager.get_state(session_id)
    
    def reset_session(self, session_id: str) -> bool:
        """Reset a session for a new topic."""
        return state_manager.reset_session(session_id)


# ============================================================================
# GLOBAL GRAPH INSTANCE
# ============================================================================

# Singleton instance for application-wide use
_agent_graph_instance: TicmiAgentGraph | None = None


def get_agent_graph() -> TicmiAgentGraph:
    """
    Get or create the global agent graph instance.
    
    Returns:
        TicmiAgentGraph singleton instance
    """
    global _agent_graph_instance
    if _agent_graph_instance is None:
        _agent_graph_instance = TicmiAgentGraph()
    return _agent_graph_instance


def create_agent_graph() -> StateGraph:
    """
    Factory function to create a new graph instance.
    Use this for testing or when you need isolated graph instances.
    
    Returns:
        Compiled StateGraph
    """
    return TicmiAgentGraph().graph
