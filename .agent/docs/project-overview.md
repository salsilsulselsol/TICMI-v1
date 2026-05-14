# TICMI Project Documentation

## Project Overview

**TICMI (Teach Me)** is an adaptive digital learning platform for High School Mathematics that uses a Multi-Agent AI architecture to detect prerequisite knowledge gaps and perform Socratic remediation based on the "Student-as-Teacher" paradigm.

## Core Philosophy

### The Protege Effect
Research shows that students learn better when they teach others. TICMI leverages this by having our AI agents act as "confused students" who need explanations from the learner, rather than traditional tutors who provide answers.

### Prerequisite-First Approach
Mathematics is hierarchical. Before addressing surface-level errors, we identify and remediate foundational gaps using:
1. **Diagnostic Assessment**: Classify error types (procedural, conceptual, arithmetic, prerequisite)
2. **Socratic Dialogue**: Guided questioning without direct answers
3. **Competency Verification**: Confirm understanding before returning to main content

## Technology Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Frontend** | Next.js 14+ (App Router) | SSR/SSG for performance, React Server Components |
| **Styling** | Tailwind CSS | Utility-first responsive design |
| **State** | Zustand | Lightweight client-side state management |
| **Visualization** | React Flow | Interactive concept dependency graphs |
| **Backend** | FastAPI | Async Python API with WebSocket support |
| **Database** | PostgreSQL + SQLModel | Relational data with Pydantic integration |
| **AI Orchestration** | LangGraph | Multi-agent workflow as directed graphs |
| **Vector Store** | ChromaDB | RAG for educational content retrieval |
| **LLM** | Google Gemini 1.5 Pro / Ollama (Llama 3) | Agent reasoning and generation |
| **Deployment** | Docker | Containerized microservices |

## Architecture Diagram

```
┌─────────────────┐     WebSocket      ┌─────────────────┐
│   Frontend      │ ◄────────────────► │   Backend       │
│   (Next.js)     │   Streaming JSON   │   (FastAPI)     │
│                 │                    │                 │
│ - Concept Map   │                    │ - REST API      │
│ - Math Input    │                    │ - WS Endpoint   │
│ - Chat UI       │                    │ - Agent Router  │
└─────────────────┘                    └────────┬────────┘
                                                │
                                                ▼
                                     ┌─────────────────┐
                                     │  LangGraph      │
                                     │  StateGraph     │
                                     │                 │
                                     │ ┌─────────────┐ │
                                     │ │ Diagnostic  │ │
                                     │ │   Agent     │ │
                                     │ └──────┬──────┘ │
                                     │        │        │
                                     │        ▼        │
                                     │ ┌─────────────┐ │
                                     │ │  Socratic   │ │
                                     │ │   Agent     │ │
                                     │ └─────────────┘ │
                                     └────────┬────────┘
                                              │
                              ┌───────────────┼───────────────┐
                              ▼               ▼               ▼
                     ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
                     │ PostgreSQL  │ │  ChromaDB   │ │  LLM API    │
                     │  (Sessions) │ │  (RAG)      │ │  (Gemini)   │
                     └─────────────┘ └─────────────┘ └─────────────┘
```

## Directory Structure

```
TICMI-v1/
├── backend/
│   ├── app/
│   │   ├── ai_agents/
│   │   │   ├── graph.py          # LangGraph StateGraph definition
│   │   │   ├── nodes.py          # Agent node implementations
│   │   │   ├── prompts/          # Markdown prompt templates
│   │   │   └── state.py          # TypedDict state schemas
│   │   ├── api/
│   │   │   └── routes.py         # REST and WebSocket endpoints
│   │   ├── models/
│   │   │   └── database.py       # SQLModel table definitions
│   │   ├── services/
│   │   │   ├── rag.py            # ChromaDB integration
│   │   │   └── llm.py            # LLM provider abstraction
│   │   └── main.py               # FastAPI application entry
│   ├── tests/
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── app/
│   │   ├── components/
│   │   ├── hooks/
│   │   ├── stores/               # Zustand stores
│   │   └── page.tsx
│   ├── public/
│   ├── tailwind.config.ts
│   └── package.json
├── .agent/
│   ├── skills/                   # Development competency docs
│   └── docs/                     # Architecture and workflow docs
├── docker-compose.yml
└── README.md
```

## Key Features

### 1. Adaptive Learning Paths
- Real-time error classification
- Dynamic routing to remediation modules
- Competency-based progression tracking

### 2. Socratic Dialogue System
- AI agents act as learners, not teachers
- Bloom's Taxonomy-aligned questioning
- No direct answer provision

### 3. Concept Mapping
- Visual prerequisite trees using React Flow
- Interactive exploration of topic dependencies
- Progress highlighting across skill networks

### 4. Session Persistence
- WebSocket connections with thread-based state
- Resume conversations across devices
- Historical analysis of learning patterns

## Development Workflow

### Setup
```bash
# Backend
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Frontend
cd frontend
npm install

# Docker (optional)
docker-compose up --build
```

### Running Agents Locally
```bash
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Testing
```bash
# Backend tests
pytest backend/tests

# Frontend tests
npm test --prefix frontend
```

## Deployment Considerations

### Why Docker?
Despite mobile-first frontend goals, Docker is essential for:
1. **Backend Consistency**: Python environment reproducibility across dev/staging/prod
2. **Microservices Isolation**: Separate containers for API, workers, and vector DB
3. **Scaling**: Horizontal scaling of agent workers during peak usage
4. **CI/CD**: Standardized build pipelines
5. **Local Development**: One-command setup for new team members

The frontend remains mobile-first PWA (Progressive Web App) served via Next.js, while Docker handles backend infrastructure.

### Environment Variables
Required secrets (use `.env` files, never commit):
- `GOOGLE_API_KEY` or `OLLAMA_HOST`
- `DATABASE_URL`
- `CHROMA_PERSIST_DIR`
- `JWT_SECRET`

## Contributing

1. Follow type hints in all Python code
2. Write prompts as separate markdown files
3. Test agent flows with mock LLM responses
4. Document new skills in `.agent/skills/`

## License

MIT License - See LICENSE file for details
