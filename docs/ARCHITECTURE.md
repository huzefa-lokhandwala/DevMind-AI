# DevMind AI Architecture Specification

DevMind AI is a code-aware Retrieval-Augmented Generation (RAG) system engineered for deep software codebase reasoning, semantic search, and architectural execution-flow tracing.

---

## 1. High-Level System Architecture

The following diagram illustrates the complete system architecture, spanning the Next.js frontend workspace, security layer, FastAPI orchestration service, hybrid retrieval engine, AST CodeGraph, PostgreSQL/pgvector persistence, and Gemini LLM provider:

```mermaid
graph TD
    Client[Next.js 14 Frontend Workspace<br/>localhost:3000] -->|HTTP / CORS / X-API-Key| Security[FastAPI Security Layer<br/>app/api/auth.py]
    
    subgraph FastAPI Backend Application [localhost:8000]
        Security -->|Validated Request| Router[API Router<br/>app/api/routes]
        Router -->|Orchestrate| Service[RAGService<br/>app/services/rag_service.py]
        
        subgraph Ingestion & Chunking Pipeline
            Service -->|Local Directory| Loader[RepositoryLoader<br/>app/loaders]
            Service -->|GitHub HTTPS URL| GHLoader[GitHubRepositoryLoader<br/>app/loaders]
            Loader --> Chunker[CodeChunker AST Parser<br/>app/chunking/code_chunker.py]
            GHLoader --> Chunker
            Chunker --> EmbedEngine[EmbeddingEngine 384d<br/>app/embeddings]
        end
        
        subgraph Hybrid Retrieval V2 Engine
            Service -->|Query String| Classifier[QueryClassifier<br/>app/retrieval/query_classifier.py]
            Classifier -->|Intent & Category| Retriever[Retriever<br/>app/retrieval/retriever.py]
            Retriever -->|Semantic Search| FAISS[FAISS Vector Store<br/>app/vector_store]
            Retriever -->|Graph BFS Expansion| Graph[CodeGraph<br/>app/graph/code_graph.py]
            Retriever -->|Lexical & Symbol Rerank| Reranker[CodeReranker & KeywordMatcher<br/>app/retrieval/reranker.py]
        end
        
        subgraph Prompting & LLM Generation
            Retriever -->|Ranked Chunks & Citations| Assembler[ContextAssembler<br/>app/prompts/context_assembler.py]
            Assembler -->|Structured Prompt| Gemini[GeminiProvider<br/>app/llm/gemini_provider.py]
            Gemini -->|gemini-3.6-flash| GeminiAPI[Google GenAI API]
        end
    end
    
    subgraph Persistence Layer
        EmbedEngine -->|Vector Embeddings| PGVector[PostgreSQL 16 + pgvector<br/>app/db]
        Service -->|Repository & Query Logs| Relational[PostgreSQL Relational Tables<br/>repositories, files, chunks, query_logs]
    end
    
    GeminiAPI -->|Generated Answer| Gemini
    Gemini -->|QueryResponse| Router
    Router -->|JSON Response| Client
```

---

## 2. Ingestion & Repository Indexing Pipeline

When a repository is submitted for indexing (via local folder path or GitHub HTTPS URL), DevMind AI executes the following ingestion pipeline:

```mermaid
sequenceDiagram
    autonumber
    actor User
    participant Frontend as Next.js Client
    participant API as FastAPI (/repositories/index)
    participant Loader as RepositoryLoader / GitHubLoader
    participant Chunker as CodeChunker (AST Parser)
    participant Embedder as EmbeddingEngine (BAAI/bge-small-en-v1.5)
    participant Stores as FAISS & PostgreSQL (pgvector)
    participant Graph as CodeGraph

    User->>Frontend: Submit repo (Path or GitHub URL)
    Frontend->>API: POST /repositories/index (X-API-Key)
    API->>Loader: Ingest files / Clone repo
    Loader-->>API: List of raw document objects
    API->>Chunker: Parse documents (Python AST & TS/JS parser)
    Chunker-->>API: CodeChunks with line ranges & symbol metadata
    API->>Embedder: Generate 384d vector embeddings
    Embedder-->>API: Embedded CodeChunks
    API->>Stores: Add to FAISS index & persist in PostgreSQL/pgvector
    API->>Graph: Build AST dependency nodes & call edges
    API-->>Frontend: IndexRepositoryResponse (files, chunks, embeddings)
```

### AST Structural Code Chunking
Unlike naive text splitters that break code arbitrarily by character or paragraph limits, `CodeChunker` ([app/chunking/code_chunker.py](file:///Users/huzefa/DevMind-AI/app/chunking/code_chunker.py)) extracts structural AST units:
- **Python Code**: Uses native Python `ast` module to extract top-level functions (`FunctionDef`), async functions (`AsyncFunctionDef`), classes (`ClassDef`), methods, and file-level imports/calls.
- **TypeScript / JavaScript Code**: Uses regex-based structural parsing supporting named imports (`import { X }`), default imports, aliased imports, namespace imports, async functions, arrow functions, methods, re-exports (`export { X }`), and call expressions.
- **Metadata Annotation**: Each chunk is annotated with `start_line`, `end_line`, `symbol_name`, `imports`, `imported_symbols`, `exported_symbols`, `function_calls`, and `repository_name`.

---

## 3. RAG V2 Retrieval & Reranking Methodology

DevMind AI uses a hybrid search and reranking algorithm to locate relevant code chunks:

```mermaid
flowchart LR
    Query[User Query] --> Intent[QueryClassifier]
    Intent -->|Detect Intent Category| Search[FAISS Over-Fetch Candidate Pool]
    Search --> Rerank[CodeReranker]
    
    subgraph Scoring Model
        Rerank --> Cosine[Semantic Cosine Similarity S_semantic]
        Rerank --> Lexical[Lexical Token Overlap S_lexical]
        Rerank --> Boost[Symbol & File Signal Boost I_symbol]
    end
    
    Cosine --> Formula[Combined Score Computation]
    Lexical --> Formula
    Boost --> Formula
    Formula --> Filter{Score >= 0.25 Threshold?}
    Filter -->|Yes| GraphCheck{Execution Flow Intent?}
    Filter -->|No| Discard[Discard Candidate]
    GraphCheck -->|Yes| BFS[CodeGraph BFS Expansion]
    GraphCheck -->|No| Final[Final Ranked Context Pool]
    BFS --> Final
```

### Hybrid Scoring Formula

$$\text{Final Score} = (w_{\text{semantic}} \cdot S_{\text{semantic}}) + (w_{\text{lexical}} \cdot S_{\text{lexical}}) + (w_{\text{symbol}} \cdot I_{\text{symbol}})$$

Where:
- $S_{\text{semantic}}$: Normalized cosine similarity score calculated by FAISS ($[0.0, 1.0]$).
- $S_{\text{lexical}}$: Token overlap ratio computed by `KeywordMatcher` ($[0.0, 1.0]$).
- $I_{\text{symbol}}$: Binary boost signal ($1.0$ if the query matches `symbol_name` or `file_path`, else $0.0$).
- Default weights: $w_{\text{semantic}} = 0.65$, $w_{\text{lexical}} = 0.25$, $w_{\text{symbol}} = 0.10$.
- Similarity Threshold: Candidates with a final score below `0.25` are automatically filtered out.

---

## 4. AST CodeGraph Architecture

`CodeGraph` ([app/graph/code_graph.py](file:///Users/huzefa/DevMind-AI/app/graph/code_graph.py)) constructs an in-memory directed dependency graph for multi-hop execution tracing:

- **Node Types**:
  - `FILE`: Source file paths (e.g., `lib/verification/engine.ts`).
  - `CLASS`: Object classes and interfaces (e.g., `VerificationEngine`).
  - `FUNCTION`: Standalone and member functions (e.g., `calculateScore`).
  - `API_ROUTE`: HTTP API handlers (e.g., `POST /api/verify`).
  - `PRISMA_MODEL`: Database entity models (e.g., `Achievement`).
- **Edge Types**: `IMPORTS`, `DEFINES`, `CALLS`, `ROUTE_CALLS`.
- **Graph BFS Expansion**: When `QueryClassifier` detects an `EXECUTION_FLOW` intent (e.g. *"Trace submission to database storage"*), the retriever triggers a Breadth-First Search (BFS) starting from retrieved entry nodes up to depth `N=2`, retrieving connected implementation files that semantic search alone might miss.

---

## 5. Security & Authentication Architecture

DevMind AI enforces multi-tenant repository isolation and API security:

- **Header Security**: Protected endpoints (`POST /query`, `POST /repositories/index`) require `X-API-Key`.
- **Constant-Time Comparison**: Key validation uses `hmac.compare_digest` in [app/api/auth.py](file:///Users/huzefa/DevMind-AI/app/api/auth.py) to eliminate timing attack vulnerabilities.
- **Fail-Closed Production Policy**: In production (`DEVMIND_ENV=production`), unconfigured API keys result in `HTTP 500 Server Security Misconfiguration`.
- **Multi-Tenant Repository Isolation**: Vector search (`FAISSVectorStore.search`) and CodeGraph lookups filter candidates by `repository_name` to prevent cross-repository retrieval contamination.
- **CORS Protection**: Configurable origins (`CORS_ORIGINS`) allow explicit cross-origin access for trusted frontend hosts.
