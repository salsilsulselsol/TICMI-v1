# LangGraph Agent Workflow Patterns

## Overview
This document outlines the standard patterns for building multi-agent workflows in TICMI using LangGraph.

## Architecture Pattern: Centralized Supervisor/Router

### State Schema Design
All agents share a typed state object. Use Python `TypedDict` or Pydantic models:

```python
from typing import TypedDict, List, Annotated
from langchain_core.messages import BaseMessage
import operator

class AgentState(TypedDict):
    messages: Annotated[List[BaseMessage], operator.add]
    current_error_type: str
    prerequisite_resolved: bool
    user_competency_level: int  # 1-5 scale
    current_concept: str
    remediation_history: List[str]
```

### Node Implementation Rules

1. **Pure Functions**: Each node must be a pure function that takes `AgentState` and returns a dict of updates
2. **No Side Effects**: Database writes and external API calls should happen in dedicated service layers
3. **Explicit Returns**: Always return a dict matching the state schema, even if empty `{}`

### Diagnostic Agent (Supervisor)

**Purpose**: Parse student input, classify errors, and route to appropriate remediation path.

**Implementation Guidelines**:
- Use few-shot prompting with examples of common math misconceptions
- Output structured JSON with fields: `error_type`, `confidence`, `suggested_route`
- Set `prerequisite_resolved = False` when gap detected

**Example Prompt Structure**:
```markdown
You are a diagnostic expert for high school mathematics.
Analyze the student's solution step and identify:
1. The specific mathematical concept they attempted
2. Whether the error is procedural, conceptual, or arithmetic
3. If it indicates a PREREQUISITE KNOWLEDGE GAP

Respond ONLY in JSON format:
{
  "error_type": "conceptual|procedural|arithmetic|prerequisite_gap",
  "missing_prerequisite": "name_of_concept" or null,
  "confidence": 0.0-1.0,
  "route_to": "socratic_remmediation|continue_module|hint_only"
}
```

### Socratic Verification Agent (Worker)

**Purpose**: Act as a "confused student" to trigger the Protege Effect. NEVER give direct answers.

**Implementation Guidelines**:
- Adopt persona: "I'm trying to understand but I'm stuck at this specific step"
- Ask questions mapped to Bloom's Taxonomy levels
- Escalate question specificity only after 3 failed attempts
- Log all interactions to `remediation_history`

**Example Prompt Structure**:
```markdown
You are a fellow student who is confused about [CONCEPT].
The learner is trying to teach you, but you have a specific gap.

Rules:
1. NEVER provide the correct answer or formula
2. Ask ONE probing question at a time
3. Frame questions as your own confusion: "I don't get why..." 
4. Use analogies from real-world contexts when appropriate
5. If the learner explains correctly, express understanding and ask follow-up

Current competency level: {user_competency_level}
Tailor your language complexity accordingly.
```

### Conditional Edge Logic

Implement hybrid routing with both LLM decisions and deterministic flags:

```python
def route_after_diagnostic(state: AgentState) -> str:
    """Deterministic routing based on diagnostic output."""
    if state["prerequisite_resolved"]:
        return "main_module"
    
    error_type = state["current_error_type"]
    if error_type == "prerequisite_gap":
        return "socratic_agent"
    elif error_type == "procedural":
        return "hint_agent"
    else:
        return "encouragement_agent"

# Add conditional edges to graph
graph.add_conditional_edges(
    source="diagnostic_agent",
    path=route_after_diagnostic,
    mapping={
        "socratic_agent": "socratic_agent",
        "main_module": "__end__",
        "hint_agent": "hint_agent",
        "encouragement_agent": "encouragement_agent"
    }
)
```

## Graph Compilation

Always compile the graph with checkpointer for session persistence:

```python
from langgraph.checkpoint.memory import MemorySaver

memory = MemorySaver()
app = graph.compile(checkpointer=memory)

# Usage with thread_id for student sessions
config = {"configurable": {"thread_id": "student_123_session_4"}}
result = app.invoke(input_state, config=config)
```

## Testing Strategies

1. **Unit Tests**: Mock LLM responses to test routing logic deterministically
2. **Integration Tests**: Run full graph with recorded student sessions
3. **Edge Cases**: Test with empty inputs, contradictory statements, and off-topic queries

## Performance Optimization

- Use streaming for long-running agent chains
- Cache RAG retrieval results per concept
- Implement timeout handlers for each node (max 30s per agent)
- Batch database writes at graph completion, not per node
