# DevMind AI

> Code-aware Retrieval-Augmented Generation (RAG) system for intelligent software repository indexing, hybrid semantic/lexical search, AST CodeGraph dependency tracing, and precise line-level LLM codebase reasoning.

[![DevMind AI CI/CD Pipeline](https://github.com/huzefa-lokhandwala/DevMind-AI/actions/workflows/ci-cd.yml/badge.svg)](https://github.com/huzefa-lokhandwala/DevMind-AI/actions/workflows/ci-cd.yml)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg?style=flat&logo=fastapi)](https://fastapi.tiangolo.com)
[![Next.js](https://img.shields.io/badge/Next.js-16.3-black.svg?style=flat&logo=next.js)](https://nextjs.org)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16%20%2B%20pgvector-blue.svg?style=flat&logo=postgresql)](https://github.com/pgvector/pgvector)
[![Pytest](https://img.shields.io/badge/Pytest-119%20Passed-success.svg?style=flat&logo=pytest)](https://pytest.org)

---

## 1. What DevMind AI Does

DevMind AI enables software developers, tech leads, and security auditors to ask natural-language questions about complex codebases and receive factually grounded, line-cited answers.

By combining **AST structural code chunking**, **768-dimensional Gemini vector embeddings**, **hybrid semantic/lexical reranking**, and **AST CodeGraph dependency traversal**, DevMind AI bridges the gap between raw vector search and true multi-file code execution flow tracing.

---

## 2. Key Features

- 🧠 **AST Structural Code Chunking**: Parses Python AST and TypeScript/JavaScript source code into discrete functions, methods, classes, and exported symbols.
- ⚡ **Advanced Hybrid Reranker**: Merges dense vector cosine similarity ($0.65$), keyword token overlap ($0.25$), and exact symbol match signals ($0.10$).
- 🕸️ **AST CodeGraph Execution Traversal**: Models multi-file dependencies (`IMPORTS`, `CALLS`, `DEFINES`, `ROUTE_CALLS`) to retrieve connected execution paths.
- 🔗 **GitHub Repository Ingestion**: Clones public GitHub repositories via secure HTTPS URL validation with timeout and path traversal protection.
- 🛡️ **Production-Grade API Security**: Enforces constant-time `X-API-Key` authentication (`hmac.compare_digest`), fail-closed production policy, and configurable CORS.
- 💾 **Dual Vector & Relational Storage**: In-memory FAISS vector store for sub-millisecond retrieval paired with PostgreSQL + `pgvector` for persistence.
- 💻 **Modern Next.js 14 Web Workspace**: Dark-themed developer UI featuring real-time backend readiness indicators, indexing drawer, prompt console, and expandable source drawers.
- 🐳 **Unified Docker Stack**: Single-command container orchestration (`docker compose up --build`) for instant local or cloud deployment.

---

## 3. Architecture Overview

```
                      [ Next.js 14 Web Workspace (Port 3000) ]
                                         │
                                   HTTP / X-API-Key
                                         │
                      [ FastAPI Backend Server (Port 8000) ]
                                         │
         ┌───────────────────────────────┼───────────────────────────────┐
         ▼                               ▼                               ▼
 [ app/chunking ]               [ app/retrieval ]               [ app/db & store ]
  - Python AST                   - Hybrid Retriever              - FAISS Vector Index
  - TS/JS Regex                  - KeywordMatcher                - PostgreSQL 16
  - Line ranges                  - CodeReranker (0.65/0.25/0.1)  - pgvector 384d
                                 - AST CodeGraph BFS
                                         │
                                         ▼
                               [ app/llm Gemini 3.6 ]
                                 - Structured Context
                                 - Line-Level Citations
```

For full specifications and sequence flow diagrams, view [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

---

## 4. Technology Stack

- **Backend**: Python 3.12, FastAPI 0.115, Uvicorn, Pydantic v2, SQLAlchemy 2.0, Alembic.
- **AI & RAG Engine**: Google GenAI SDK (`gemini-3.6-flash`, `gemini-embedding-001`), FAISS (`faiss-cpu`), Custom AST Chunker & CodeGraph.
- **Frontend**: Next.js 16 (App Router), React 19, TypeScript, TailwindCSS, Lucide Icons, React Markdown.
- **Database**: PostgreSQL 16 with `pgvector` extension.
- **Containerization & CI/CD**: Docker, Docker Compose, GitHub Actions.

---

## 5. Repository Structure

```
DevMind-AI/
├── app/                        # FastAPI Backend Application Root
│   ├── api/                    # API Routers, Authentication, & Pydantic Schemas
│   │   ├── auth.py             # Constant-time X-API-Key Security Dependency
│   │   └── routes/             # Endpoint Handlers (/health, /query, /repositories/index)
│   ├── chunking/               # AST Structural Code Chunker
│   ├── db/                     # SQLAlchemy ORM Models & Session Management
│   ├── embeddings/             # Gemini 768d Embedding Engine
│   ├── evaluation/             # RAG Benchmark Metrics Evaluator
│   ├── graph/                  # AST CodeGraph Node & Dependency Edge Traversal
│   ├── llm/                    # Gemini Provider Interface
│   ├── loaders/                # RepositoryLoader & GitHubRepositoryLoader
│   ├── prompts/                # ContextAssembler & Prompt Templates
│   ├── retrieval/              # Hybrid Retriever, KeywordMatcher, & CodeReranker
│   ├── services/               # RAGService Application Lifecycle Coordinator
│   └── vector_store/           # FAISS Vector Store Manager
├── frontend/                   # Next.js 14 Developer Web Application Workspace
│   ├── app/                    # Next.js App Router Pages & Styles
│   ├── components/             # React UI Components (Navbar, IndexModal, AnswerView, etc.)
│   ├── lib/                    # Typed API Client & Pydantic Interface Definitions
│   ├── Dockerfile              # Multi-Stage Production Standalone Dockerfile
│   └── __tests__/              # Vitest Unit Tests
├── docs/                       # Comprehensive Technical Documentation
│   ├── ARCHITECTURE.md         # System Architecture Specification & Sequence Flows
│   ├── API.md                  # REST API Specification & Endpoint Schema
│   ├── DEPLOYMENT.md           # Production Container Deployment Guide
│   └── TESTING.md              # Test Suite & Quality Assurance Guide
├── .github/workflows/          # GitHub Actions CI/CD Pipeline (ci-cd.yml)
├── docker-compose.yml          # Unified Single-Command Docker Compose Manifest
├── docker-compose.prod.yml     # Production Docker Compose Profile Override
├── .env.example                # Development Environment Variable Template
├── .env.production.example     # Production Environment Variable Template
└── tests/                      # Backend Pytest Test Suite (114 Tests)
```

---

## 6. Local Development Setup

### Prerequisites
- **Python 3.10+**
- **Node.js 20+**
- **Docker Desktop**

### Quickstart

1. **Clone the Repository**:
   ```bash
   git clone https://github.com/huzefa-lokhandwala/DevMind-AI.git
   cd DevMind-AI
   ```

2. **Configure Environment Variables**:
   ```bash
   cp .env.example .env
   # Edit .env and set GEMINI_API_KEY=your_gemini_key
   ```

3. **Start Local Docker Services**:
   ```bash
   docker compose up -d
   ```

4. **Install Backend Dependencies & Apply Migrations**:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   alembic upgrade head
   ```

5. **Start FastAPI Backend Server**:
   ```bash
   uvicorn app.api.main:app --reload --port 8000
   ```

6. **Start Frontend Web Application**:
   ```bash
   cd frontend
   npm install
   npm run dev
   ```
   Access the web workspace at [http://localhost:3000](http://localhost:3000).

---

## 7. Unified Docker Compose Deployment

Run the complete containerized stack (FastAPI backend + Next.js frontend + pgvector PostgreSQL) with a single command:

```bash
docker compose up --build -d
```

- **Frontend Workspace**: [http://localhost:3000](http://localhost:3000)
- **Backend API**: [http://localhost:8000](http://localhost:8000)

### Production Docker Profile
For production environments requiring log rotation, restart policies, and healthcheck tuning:

```bash
cp .env.production.example .env
docker compose -f docker-compose.yml -f docker-compose.prod.yml up --build -d
```

For complete deployment procedures, view [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md).

---

## 8. API Overview

| Method | Endpoint | Auth | Purpose |
|---|---|---|---|
| `GET` | `/health` | Public | Returns service health status |
| `GET` | `/health/ready` | Public | Verifies application & PostgreSQL database connectivity |
| `POST` | `/repositories/index` | `X-API-Key` | Indexes local directory path or clones public GitHub HTTPS URL |
| `POST` | `/query` | `X-API-Key` | Queries indexed codebase and returns line-cited AI answer |

For complete payload schemas, curl examples, and status code specifications, view [docs/API.md](docs/API.md).

---

## 9. GitHub Repository Indexing Workflow

1. Submit a public HTTPS GitHub URL (e.g. `https://github.com/huzefa-lokhandwala/proofos`) via the Web UI modal or `POST /repositories/index`.
2. `GitHubRepositoryLoader` validates URL format, domain, and HTTPS scheme.
3. The repo is cloned via shallow depth (`--depth 1`) into `data/cloned_repos/owner/repo`.
4. `CodeChunker` parses source files into AST function/class chunks.
5. `EmbeddingEngine` generates 768d vector embeddings and stores them in FAISS and PostgreSQL `pgvector`.

---

## 10. Query & Answer Generation Workflow

1. User enters a query (e.g. *"Where is VerificationEngine implemented?"*).
2. `QueryClassifier` determines query intent category (`EXECUTION_FLOW`, `SYMBOL_LOOKUP`, `GENERAL`).
3. `FAISSVectorStore` over-fetches dense vector candidates based on cosine similarity.
4. `CodeReranker` computes hybrid scores ($0.65 \cdot S_{\text{semantic}} + 0.25 \cdot S_{\text{lexical}} + 0.10 \cdot I_{\text{symbol}}$).
5. If `EXECUTION_FLOW` is detected, `CodeGraph` traverses AST import and call edges to expand context.
6. `ContextAssembler` builds structured prompts containing relevant code snippets and line numbers.
7. `GeminiProvider` sends prompt to `gemini-3.6-flash` and returns markdown answer with source citations.

---

## 11. Testing & Quality Assurance

- **Backend Pytest Suite**: 119 tests passing (`.venv/bin/python -m pytest -v`).
- **Frontend Vitest Suite**: 8 tests passing (`cd frontend && npx vitest run`).
- **Next.js Production Build**: Standalone output verification (`cd frontend && npm run build`).
- **Docker Validation**: `docker compose config`.

For full test coverage breakdown, view [docs/TESTING.md](docs/TESTING.md).

---

## 12. Continuous Integration & Deployment (CI/CD)

Every push or pull-request to `main` triggers automated GitHub Actions workflow (`.github/workflows/ci-cd.yml`):
- **Backend Test**: Runs 114 pytest tests against live PostgreSQL + pgvector container.
- **Frontend Test & Build**: Runs Vitest unit tests and builds Next.js production standalone bundle.
- **Docker Compose Build**: Validates `docker compose config` and image builds.

---

## 13. Health & Readiness Endpoints

- Health Check: `curl http://localhost:8000/health` -> `{"status":"ok","service":"DevMind AI"}`
- Database Readiness: `curl http://localhost:8000/health/ready` -> `{"status":"ready","database":"connected","service":"DevMind AI"}`

---

## 14. Troubleshooting & Known Limitations

- **Initial Container Startup**: On initial launch, downloading the `BAAI/bge-small-en-v1.5` HuggingFace embedding cache inside the container takes 30-40 seconds. Backend healthcheck includes a 60s start period to accommodate initial download.
- **Deprecation Warnings**:
  - `StarletteDeprecationWarning` regarding `httpx` in Starlette test client (harmless upstream deprecation).
  - `google.genai.types` Python 3.17 deprecation notice (harmless upstream SDK warning).

---

## 15. License

This project is open-source software licensed under the [MIT License](LICENSE).
