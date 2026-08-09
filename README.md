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
  │
  ▼
FAISSVectorStore (app/vector_store)
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

## Setup & Environment Activation

Activate the virtual environment:

```bash
source .venv/bin/activate
pip install -r requirements.txt
```

Set up environment variables:

```bash
cp .env.example .env
# Add GEMINI_API_KEY or GOOGLE_API_KEY in .env
```

## Running Tests

Run the full pytest suite (65 tests):

```bash
.venv/bin/pytest -v
```

## Running the CLI Pipeline

Run the CLI pipeline demonstration:

```bash
.venv/bin/python main.py
```

## Running the FastAPI Server

Start the API server with live reloading:

```bash
.venv/bin/uvicorn app.api.main:app --reload
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
  "model": "gemini-2.5-flash",
  "latency_ms": 123.45
}
```
