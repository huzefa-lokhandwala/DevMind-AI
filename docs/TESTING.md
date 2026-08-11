# DevMind AI Testing & Quality Assurance Guide

Comprehensive documentation of automated test suites, test categories, commands, and continuous integration procedures.

---

## 1. Executive Test Summary

| Test Suite | Framework | Total Tests | Status | Execution Time |
|---|---|---|---|---|
| **Backend Test Suite** | Pytest 9.1 | **114** | ✅ **PASSing** | ~9.9s |
| **Frontend Test Suite** | Vitest 4.1 | **8** | ✅ **PASSing** | ~0.3s |
| **Next.js Production Build** | Next.js 16 (Turbopack) | **Standalone** | ✅ **PASSing** | ~2.8s |
| **Docker Compose Config** | Docker CLI | **Full Stack** | ✅ **PASSing** | ~0.2s |

---

## 2. Backend Test Suite (`pytest`)

The backend test suite verifies vector search accuracy, AST symbol extraction, database models, RAG V2 execution flow, multi-tenant repository isolation, and security dependencies.

### Command:
```bash
.venv/bin/python -m pytest -v
```

### Test Module Breakdown (114 Tests):

| Test Module | Description | Test Count |
|---|---|---|
| `tests/test_adversarial.py` | Missing context, non-existent symbols, duplicate symbol resolution | 4 |
| `tests/test_api.py` | FastAPI routes, input validation, 400/422 error handling | 14 |
| `tests/test_auth_and_cors.py` | `X-API-Key` auth, fail-closed policy, CORS OPTIONS preflight | 8 |
| `tests/test_code_chunker.py` | Python AST & TS/JS structural parser, line ranges, symbol extraction | 7 |
| `tests/test_context_assembler.py` | Prompt context assembly, deduplication, max char truncation | 6 |
| `tests/test_database.py` | SQLAlchemy ORM models, pgvector embedding columns, CRUD operations | 10 |
| `tests/test_embedding_engine.py` | BAAI/bge-small-en-v1.5 384d vector embedding generation | 6 |
| `tests/test_evaluation.py` | IR metrics (Recall@K, MRR, Top-1 accuracy calculation) | 5 |
| `tests/test_faiss_store.py` | FAISS index building, cosine search, metadata preservation | 6 |
| `tests/test_gemini_provider.py` | Gemini 3.6 Flash LLM provider interface, retry logic, error mapping | 4 |
| `tests/test_github_loader.py` | GitHub HTTPS URL validation, git clone execution, timeout handling | 6 |
| `tests/test_persistence_reliability.py` | Database persistence & restart reliability verification | 1 |
| `tests/test_rag_v2.py` | RAG V2 execution flow expansion, line citations, intent classification | 10 |
| `tests/test_repository_isolation.py` | Multi-tenant vector store & retriever repository isolation | 2 |
| `tests/test_repository_loader.py` | Local file reading, path traversal prevention, content loading | 3 |
| `tests/test_retrieval_advanced.py` | `KeywordMatcher`, `CodeReranker`, similarity threshold filtering | 5 |
| `tests/test_retriever.py` | Hybrid retriever, production code prioritization over tests/docs | 4 |
| `tests/test_ts_parser_assessment.py` | 13 TypeScript import/export/function/call parsing patterns | 13 |

---

## 3. Frontend Test Suite (`vitest`)

The frontend test suite verifies the typed API client layer, `localStorage` API key handling, masking formatters, and error translation.

### Command:
```bash
cd frontend && npx vitest run
```

### Test Coverage (`frontend/__tests__/api-client.test.ts`):
- `localStorage` API key persistence & clearing.
- Masked API key representation formatting (`••••••••abcd`).
- `checkHealth()` & `checkReadiness()` fetch execution.
- `queryCodebase()` sending `X-API-Key` header & parsing `QueryResponse`.
- `indexRepository()` sending `X-API-Key` header & parsing `IndexRepositoryResponse`.
- Error boundary translation (`401` -> `AuthError`, `422` -> `ValidationError`).

---

## 4. Next.js Production Standalone Build Verification

Verifies TypeScript compilation, page static optimization, and standalone server output:

```bash
cd frontend && npm run build
```

---

## 5. Docker Compose Stack Validation

Verifies Compose syntax, service dependencies, environment variable substitution, and port mappings:

```bash
docker compose config
```

---

## 6. GitHub Actions CI/CD Pipeline (`.github/workflows/ci-cd.yml`)

Every push or pull-request to `main` triggers automated CI validation:

1. **`backend-test` Job**: Runs Python 3.12 pytest suite against live PostgreSQL + pgvector container.
2. **`frontend-test-and-build` Job**: Runs Node.js 20 Vitest unit tests and compiles Next.js production standalone bundle.
3. **`docker-compose-build` Job**: Validates `docker compose config` and container image builds.

---

## 7. Known Deprecation Warnings

1. `StarletteDeprecationWarning`: `starlette.testclient.TestClient` deprecation notice regarding `httpx` (harmless third-party deprecation warning).
2. `google.genai.types`: `_UnionGenericAlias` Python 3.17 deprecation notice (harmless third-party SDK notice).
