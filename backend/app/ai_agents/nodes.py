"""
Agent Node Implementations for LangGraph Multi-Agent Workflow.

Each node is a Python function that:
1. Reads from the shared GraphState
2. Performs its specific task (diagnosis, socratic questioning, etc.)
3. Returns updates to the state
"""

from typing import Dict, Any, List
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
import json

from .llm_provider import get_llm, get_llm_with_structured_output
from ..schemas.agent import DiagnosticResult, SocraticQuery


# ============================================================================
# ENTRY NODE
# ============================================================================

async def entry_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Entry point node that initializes the conversation flow.
    
    This node:
    - Adds the user's message to conversation history
    - Resets diagnostic flags for new input
    - Prepares state for diagnostic agent
    
    Args:
        state: Current graph state
        
    Returns:
        State updates for next node
    """
    # The user message should already be in state from the API layer
    # This node just ensures proper initialization
    
    return {
        "diagnostic_complete": False,
        "socratic_turns": 0,
    }


# ============================================================================
# DIAGNOSTIC AGENT NODE (Supervisor/Router)
# ============================================================================

DIAGNOSTIC_SYSTEM_PROMPT = """You are a Diagnostic Agent for a mathematics learning platform.
Your role is to analyze student responses and identify knowledge gaps.

TASKS:
1. Parse the student's mathematical input and reasoning
2. Classify any errors into categories:
   - "algebraic_manipulation": Errors in algebra operations
   - "arithmetic": Basic calculation errors
   - "conceptual": Misunderstanding of mathematical concepts
   - "procedural": Wrong sequence of steps
   - "prerequisite_gap": Missing foundational knowledge
3. Determine if the error stems from a prerequisite knowledge gap
4. Route the conversation appropriately:
   - "socratic": Use Socratic method for prerequisite gaps
   - "direct_answer": Simple mistakes that need quick correction
   - "back_to_main": No errors detected, continue with main lesson

IMPORTANT:
- Be precise in identifying the specific missing concept
- Consider the student's competency level when diagnosing
- High confidence (>0.8) required for prerequisite gap diagnosis

Respond ONLY with valid JSON matching the DiagnosticResult schema."""


async def diagnostic_agent_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Diagnostic Agent Node - Analyzes student input and routes conversation.
    
    This is the Supervisor/Router node that:
    - Parses the user's math input
    - Classifies error types
    - Determines if it's a prerequisite gap
    - Routes to appropriate next node
    
    Args:
        state: Current graph state with messages
        
    Returns:
        State updates including diagnostic results and routing decision
    """
    messages = state.get("messages", [])
    current_topic = state.get("current_topic", "general_mathematics")
    competency_level = state.get("user_competency_level", "intermediate")
    
    if not messages:
        return {"current_error_type": None, "diagnostic_complete": True}
    
    # Get the last user message
    last_message = messages[-1]
    if not isinstance(last_message, HumanMessage):
        return {"current_error_type": None, "diagnostic_complete": True}
    
    # Build context from conversation history
    conversation_context = "\n".join([
        f"{type(msg).__name__}: {msg.content}" 
        for msg in messages[-6:]  # Last 6 messages for context
    ])
    
    # Get LLM with structured output
    llm = get_llm_with_structured_output(DiagnosticResult)
    
    # Create diagnostic prompt
    system_message = SystemMessage(content=DIAGNOSTIC_SYSTEM_PROMPT)
    user_message = HumanMessage(
        content=f"""Analyze this student interaction in the context of {current_topic}.
Student competency level: {competency_level}

Conversation:
{conversation_context}

Provide your diagnostic assessment."""
    )
    
    try:
        # Invoke LLM for structured diagnostic result
        response = await llm.ainvoke([system_message, user_message])
        
        # Parse the structured response
        if hasattr(response, 'parsed'):
            diagnostic_result: DiagnosticResult = response.parsed
        else:
            # Fallback: try to parse as JSON
            diagnostic_dict = json.loads(response.content) if isinstance(response.content, str) else response.content
            diagnostic_result = DiagnosticResult(**diagnostic_dict)
        
        # Update state based on diagnosis
        state_updates = {
            "current_error_type": diagnostic_result.error_type if diagnostic_result.error_detected else None,
            "diagnostic_complete": True,
            "prerequisite_resolved": False,  # Will be updated by socratic agent if needed
        }
        
        # Add diagnostic message to conversation
        if diagnostic_result.error_detected:
            diagnostic_msg = AIMessage(
                content=f"I've analyzed your response. I noticed a potential area we should explore: {diagnostic_result.error_type or 'a concept'}."
            )
            state_updates["messages"] = [diagnostic_msg]
        
        return state_updates
        
    except Exception as e:
        # Fallback: assume no error detected on failure
        return {
            "current_error_type": None,
            "diagnostic_complete": True,
            "messages": [AIMessage(content="Let me think about your approach...")]
        }


# ============================================================================
# SOCRATIC VERIFICATION AGENT NODE (Worker)
# ============================================================================

SOCRATIC_SYSTEM_PROMPT = """You are a Socratic Verification Agent acting as a "confused student" (Protege Effect).
Your role is NOT to give answers, but to ask probing questions that help the student discover their own errors.

PRINCIPLES:
1. NEVER give the direct answer or solution
2. Ask questions based on Bloom's Taxonomy:
   - Remember: Recall facts or basic concepts
   - Understand: Explain ideas or concepts
   - Apply: Use information in new situations
   - Analyze: Draw connections among ideas
   - Evaluate: Justify a stand or decision
   - Create: Produce new or original work
3. Act genuinely curious and slightly confused - make the student feel like they're teaching you
4. Start with higher-order questions and scaffold down if needed
5. Celebrate when students articulate correct concepts

CONTEXT:
- The student has a prerequisite knowledge gap in: {missing_concept}
- The error type is: {error_type}
- Student's competency level: {competency_level}

STRATEGY:
1. First turn: Ask an "Understand" or "Apply" level question about the missing concept
2. If student struggles: Move to "Remember" level with a concrete example
3. If student succeeds: Ask them to explain their reasoning ("Analyze" level)
4. Maximum 3 hints before providing more direct guidance

RESPOND with a SocraticQuery containing:
- A single, focused probing question
- The Bloom's Taxonomy level of your question
- Hint level (start at 0, increase if student struggles)
- The concept you expect them to articulate
- Your follow-up strategy based on their anticipated response"""


async def socratic_agent_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Socratic Verification Agent Node - Asks probing questions using Protege Effect.
    
    This worker node:
    - Acts as a "confused student" to trigger the Protege Effect
    - Asks Bloom's Taxonomy-based probing questions
    - NEVER gives direct answers
    - Tracks number of socratic turns
    
    Args:
        state: Current graph state with diagnostic info
        
    Returns:
        State updates with socratic question and incremented turn count
    """
    messages = state.get("messages", [])
    error_type = state.get("current_error_type", "unknown")
    competency_level = state.get("user_competency_level", "intermediate")
    socratic_turns = state.get("socratic_turns", 0)
    
    # Infer missing concept from error type (in production, use RAG from ChromaDB)
    missing_concept_map = {
        "algebraic_manipulation": "distributive_property_and_equation_solving",
        "arithmetic": "order_of_operations",
        "conceptual": "fundamental_concept_definition",
        "procedural": "problem_solving_steps",
        "prerequisite_gap": "foundational_prerequisite",
    }
    missing_concept = missing_concept_map.get(error_type, "related_mathematical_concept")
    
    # Limit socratic turns to prevent frustration
    if socratic_turns >= 5:
        return {
            "prerequisite_resolved": True,  # Force exit after max turns
            "messages": [AIMessage(
                content="You've thought deeply about this! Let me share some insights that might help clarify things..."
            )]
        }
    
    # Get LLM with structured output
    llm = get_llm_with_structured_output(SocraticQuery)
    
    # Build conversation context
    conversation_context = "\n".join([
        f"{type(msg).__name__}: {msg.content}" 
        for msg in messages[-8:]
    ])
    
    # Create socratic prompt
    system_message = SystemMessage(
        content=SOCRATIC_SYSTEM_PROMPT.format(
            missing_concept=missing_concept,
            error_type=error_type,
            competency_level=competency_level
        )
    )
    
    user_message = HumanMessage(
        content=f"""Based on this conversation, generate a Socratic question to help the student discover their knowledge gap.

Conversation:
{conversation_context}

Current socratic turn: {socratic_turns + 1}

Generate your probing question."""
    )
    
    try:
        # Invoke LLM for structured socratic query
        response = await llm.ainvoke([system_message, user_message])
        
        # Parse the structured response
        if hasattr(response, 'parsed'):
            socratic_query: SocraticQuery = response.parsed
        else:
            # Fallback: try to parse as JSON
            socratic_dict = json.loads(response.content) if isinstance(response.content, str) else response.content
            socratic_query = SocraticQuery(**socratic_dict)
        
        # Create the socratic question message
        socratic_message = AIMessage(
            content=f"Hmm, I'm a bit confused about something... {socratic_query.question}"
        )
        
        return {
            "messages": [socratic_message],
            "socratic_turns": socratic_turns + 1,
        }
        
    except Exception as e:
        # Fallback: generic socratic question
        fallback_question = "Can you walk me through how you arrived at that answer? I want to make sure I understand your thinking."
        return {
            "messages": [AIMessage(content=f"Hmm, I'm wondering... {fallback_question}")],
            "socratic_turns": socratic_turns + 1,
        }


# ============================================================================
# RESOLUTION CHECK NODE
# ============================================================================

async def resolution_check_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Checks if the prerequisite gap has been resolved.
    
    This node analyzes the student's latest response to determine
    if they've demonstrated understanding of the missing concept.
    
    Args:
        state: Current graph state
        
    Returns:
        State updates with prerequisite_resolved flag
    """
    messages = state.get("messages", [])
    
    # Get last student response
    student_messages = [m for m in messages if isinstance(m, HumanMessage)]
    if not student_messages:
        return {"prerequisite_resolved": False}
    
    last_student_response = student_messages[-1].content
    
    # Simple heuristic: check for confidence indicators
    # In production, use LLM to evaluate understanding
    confidence_indicators = [
        "because", "therefore", "so", "that means",
        "i understand", "now i see", "got it"
    ]
    
    has_confidence = any(indicator in last_student_response.lower() 
                        for indicator in confidence_indicators)
    
    return {
        "prerequisite_resolved": has_confidence
    }
