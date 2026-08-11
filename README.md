# DevMind AI

Code-aware RAG (Retrieval-Augmented Generation) application for indexing, searching, and querying software codebases.

## Architecture

```
Repository (Local or GitHub URL)
  │
  ▼
RepositoryLoader / GitHubRepositoryLoader (app/loaders)
  │
  ▼
CodeChunker (app/chunking)
  │
  ▼
EmbeddingEngine (app/embeddings)
  ├── SentenceTransformer (BAAI/bge-small-en-v1.5, 384d)
  │
  ├──► FAISSVectorStore (app/vector_store) -- In-memory search index
  └──► PostgreSQL + pgvector (app/db) ------ Relational & Vector persistence
  │
  ▼
Advanced Hybrid Retriever & CodeReranker (app/retrieval)
  ├── Semantic Cosine Similarity (FAISS over-fetch)
  ├── Lexical Keyword Overlap (KeywordMatcher)
  ├── Code Symbol Signals (function, class, file name match boost)
  └── Similarity Threshold Filtering
  │
  ▼
ContextAssembler (app/prompts)
  │
  ▼
GeminiProvider (app/llm)
  │
  ▼
FastAPI Backend (app/api)
```

## Hybrid Reranking & Scoring Methodology

Pure dense vector embeddings can struggle with exact identifier matches in codebases (such as specific function names like `login` or `getUserById`). DevMind AI implements a transparent hybrid scoring and reranking model:

$$\text{Final Score} = (\text{semantic\_weight} \times S_{\text{semantic}}) + (\text{keyword\_weight} \times S_{\text{lexical}}) + (\text{symbol\_boost} \times I_{\text{symbol}})$$

Where:
- $S_{\text{semantic}}$: Direct normalized cosine similarity score ($[0.0, 1.0]$).
- $S_{\text{lexical}}$: Token overlap ratio between query and chunk content ($[0.0, 1.0]$).
- $I_{\text{symbol}}$: Binary boost signal ($1.0$ if query matches `function_name`, `class_name`, or `file_name`, else $0.0$).
- Default weights: `semantic_weight = 0.65`, `keyword_weight = 0.25`, `symbol_boost = 0.10`.
- Candidates with combined scores below `similarity_threshold` (default `0.25`) are filtered out prior to prompt assembly.

## Local Development Setup

### Requirements:
- Python 3.10+
- Docker Desktop (for PostgreSQL + pgvector container)

### Step-by-Step Setup:

1. **Create & Activate Virtual Environment**:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

2. **Install Dependencies**:
   ```bash
   .venv/bin/pip install -r requirements.txt
   ```

3. **Configure Environment Variables**:
   ```bash
   cp .env.example .env
   # Ensure .env contains GEMINI_API_KEY and DATABASE_URL
   ```

4. **Start PostgreSQL + pgvector Container**:
   ```bash
   docker compose up -d
   ```

5. **Run Alembic Migrations**:
   ```bash
   .venv/bin/alembic upgrade head
   ```

6. **Run Test Suite**:
   ```bash
   .venv/bin/pytest -v
   ```

7. **Run CLI Application**:
   ```bash
   .venv/bin/python main.py
   ```

8. **Run FastAPI Backend Server**:
   ```bash
   .venv/bin/uvicorn app.api.main:app --reload
   ```

## Production Deployment & CI/CD Pipeline

### Unified Single-Command Docker Stack:
To run the full production containerized application (FastAPI backend + Next.js frontend + pgvector PostgreSQL):

```bash
docker compose up --build -d
```
- **Frontend Workspace**: [http://localhost:3000](http://localhost:3000)
- **Backend API**: [http://localhost:8000](http://localhost:8000)

### Production Container Profile:
For production environments with resource limits, log rotation, and strict security:

```bash
cp .env.production.example .env
docker compose -f docker-compose.yml -f docker-compose.prod.yml up --build -d
```

### GitHub Actions CI/CD Pipeline (`.github/workflows/ci-cd.yml`):
Every push or pull-request to `main` triggers automated validation:
- **Backend**: Runs Python 3.12 pytest suite against live PostgreSQL + pgvector container.
- **Frontend**: Runs Node 20 Vitest unit tests and builds Next.js production standalone bundle.
- **Docker**: Validates `docker compose config` and container image compilation.

## RAG Evaluation Benchmark

DevMind AI includes an automated, offline evaluation benchmark (`app/evaluation`) measuring standard information retrieval metrics against ground-truth codebase questions.

### Measured Metrics:

| Metric | Baseline (Pure Semantic) | Improved (Hybrid + Reranking) |
| :--- | :--- | :--- |
| **Top-1 Accuracy** | 1.0000 | 1.0000 |
| **Recall@3** | 1.0000 | 1.0000 |
| **Recall@5** | 1.0000 | 1.0000 |
| **MRR (Mean Reciprocal Rank)** | 1.0000 | 1.0000 |

### How to Run Evaluation Benchmark:

```bash
.venv/bin/python -m app.evaluation
```

## API Endpoints

### 1. Health Check
`GET /health`

**Response:**
```json
{
  "status": "ok",
  "service": "DevMind AI"
}
```

### 2. Index Repository (Local Path or GitHub URL)
`POST /repositories/index`

**Local Request:**
```json
{
  "repository_path": "repositories/sample_project"
}
```

**GitHub Request:**
```json
{
  "github_url": "https://github.com/octocat/Spoon-Knife"
}
```

**Response:**
```json
{
  "repository": "sample_project",
  "files_loaded": 2,
  "chunks_created": 2,
  "embeddings_created": 2,
  "status": "indexed"
}
```

### 3. Query Codebase
`POST /query`

**Request:**
```json
{
  "query": "Where is login implemented?",
  "top_k": 5
}
```

**Response:**
```json
{
  "answer": "The `login()` function is implemented in `auth.py` (lines 6-13)...",
  "sources": [
    {
      "repository": "sample_project",
      "file": "auth.py",
      "symbol": "login",
      "start_line": 6,
      "end_line": 13,
      "score": 1.0
    }
  ],
  "provider": "gemini",
  "model": "gemini-3.6-flash",
  "latency_ms": 123.45
}
```
