# TICMI Development Skills

## Core Competencies

### 1. LangGraph Multi-Agent Orchestration
- **State Management**: Designing typed state schemas using `TypedDict` or Pydantic for shared agent memory
- **Node Implementation**: Creating Python functions as graph nodes that read/write from shared state
- **Conditional Routing**: Implementing hybrid LLM-based and deterministic edge transitions
- **Supervisor Pattern**: Building central router agents that classify errors and delegate to worker agents
- **Socratic Prompting**: Crafting prompts that enforce "Student-as-Teacher" paradigm without revealing answers

### 2. FastAPI WebSocket Streaming
- **Async Endpoints**: Building non-blocking WebSocket handlers for real-time AI reasoning streams
- **Message Protocols**: Defining JSON schemas for client-server agent communication
- **Connection Management**: Handling multiple concurrent student sessions with isolated state

### 3. Next.js 14+ App Router
- **Server Components**: Leveraging RSC for initial concept map rendering
- **Client State**: Managing complex UI state with Zustand for interactive math inputs
- **React Flow Integration**: Building dynamic concept dependency graphs

### 4. Educational Psychology Integration
- **Bloom's Taxonomy**: Mapping probing questions to cognitive levels (Remember → Create)
- **Prerequisite Detection**: Identifying knowledge gaps through error pattern classification
- **Competency Modeling**: Tracking user progression through skill trees

### 5. RAG with ChromaDB
- **Vector Embeddings**: Indexing mathematical concepts and common misconceptions
- **Context Retrieval**: Fetching relevant remediation strategies based on error type
- **Hybrid Search**: Combining semantic similarity with metadata filtering

## Tool Proficiency

| Tool | Usage Context |
|------|---------------|
| `langgraph` | Agent workflow orchestration |
| `langchain` | LLM abstraction and prompt templates |
| `chromadb` | Vector store for educational content |
| `fastapi` | Backend API and WebSocket server |
| `sqlmodel` | Database ORM with Pydantic integration |
| `nextjs` | Frontend framework with App Router |
| `zustand` | Lightweight client state management |
| `react-flow` | Interactive concept mapping visualization |
| `tailwindcss` | Utility-first styling for responsive UI |
| `docker` | Containerization for consistent dev/prod environments |

## Best Practices

1. **Type Safety First**: Always define explicit types for agent state and message payloads
2. **Deterministic Fallbacks**: Never rely solely on LLM routing; include boolean flags for critical paths
3. **Prompt Isolation**: Keep agent system prompts in separate markdown files for version control
4. **Streaming UX**: Show intermediate reasoning steps to build student trust in AI decisions
5. **Accessibility**: Ensure math input methods support keyboard navigation and screen readers
