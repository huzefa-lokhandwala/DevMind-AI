# DevMind AI API Specification

Complete OpenAPI documentation for DevMind AI REST API endpoints.

Base URL (Local Development & Docker): `http://localhost:8000`

---

## Authentication & Headers

Protected endpoints require an `X-API-Key` request header.

```http
X-API-Key: your_devmind_api_key
Content-Type: application/json
Accept: application/json
```

If `DEVMIND_API_KEY` is configured on the backend, missing or invalid `X-API-Key` headers will return `HTTP 401 Unauthorized`.

---

## 1. System Health Check

Returns service identification and basic application status.

- **Method**: `GET`
- **Path**: `/health`
- **Authentication**: None (Public)

### Response (`HTTP 200 OK`)
```json
{
  "status": "ok",
  "service": "DevMind AI"
}
```

### Example `curl` Request
```bash
curl -i http://localhost:8000/health
```

---

## 2. System & Database Readiness Probe

Checks application readiness and PostgreSQL + pgvector database connectivity.

- **Method**: `GET`
- **Path**: `/health/ready`
- **Authentication**: None (Public)

### Success Response (`HTTP 200 OK`)
```json
{
  "status": "ready",
  "database": "connected",
  "service": "DevMind AI"
}
```

### Error Response (`HTTP 503 Service Unavailable`)
```json
{
  "detail": {
    "status": "not_ready",
    "database": "disconnected",
    "error": "connection failed: Connection refused"
  }
}
```

### Example `curl` Request
```bash
curl -i http://localhost:8000/health/ready
```

---

## 3. Index Repository

Indexes a local software repository directory or clones and indexes a public GitHub repository.

- **Method**: `POST`
- **Path**: `/repositories/index`
- **Authentication**: Required (`X-API-Key`)

### Request Body (`IndexRepositoryRequest`)

Provide **either** `repository_path` OR `github_url`, but not both.

```json
{
  "repository_path": "repositories/sample_project",
  "github_url": null
}
```

**GitHub Request Example**:
```json
{
  "repository_path": null,
  "github_url": "https://github.com/huzefa-lokhandwala/proofos"
}
```

### Response (`HTTP 200 OK`)
```json
{
  "repository": "proofos",
  "files_loaded": 40,
  "chunks_created": 40,
  "embeddings_created": 40,
  "status": "indexed"
}
```

### Status Codes & Error Responses

| Status Code | Description | Error Detail Example |
|---|---|---|
| `200 OK` | Repository indexed successfully | Result statistics |
| `400 Bad Request` | Invalid input or git clone failed | `{"detail": "Either 'repository_path' or 'github_url' must be supplied."}` |
| `401 Unauthorized` | Missing or invalid API key | `{"detail": "Invalid or missing API key."}` |
| `422 Unprocessable Entity` | Schema validation error | `{"detail": "Provide either 'repository_path' or 'github_url', not both."}` |
| `500 Internal Server Error` | Unexpected server processing error | `{"detail": "Failed to index repository due to an internal server error."}` |

### Example `curl` Request
```bash
curl -i -X POST http://localhost:8000/repositories/index \
  -H "X-API-Key: secret_key_123" \
  -H "Content-Type: application/json" \
  -d '{"github_url": "https://github.com/huzefa-lokhandwala/proofos"}'
```

---

## 4. Query Codebase

Submits a natural-language query to retrieve relevant source code context and generate an AI answer.

- **Method**: `POST`
- **Path**: `/query`
- **Authentication**: Required (`X-API-Key`)

### Request Body (`QueryRequest`)

```json
{
  "query": "Where is VerificationEngine implemented?",
  "top_k": 5
}
```

| Parameter | Type | Default | Constraint | Description |
|---|---|---|---|---|
| `query` | `string` | **Required** | Non-empty string | Natural language codebase query |
| `top_k` | `integer` | `5` | `top_k > 0` | Maximum number of context chunks to retrieve |

### Success Response (`HTTP 200 OK`)

```json
{
  "answer": "### Implementation Location\n\nThe `VerificationEngine` class is implemented in `lib/verification/engine.ts` (lines 13-156)...",
  "sources": [
    {
      "repository": "proofos",
      "file": "engine.ts",
      "symbol": "VerificationEngine",
      "start_line": 13,
      "end_line": 156,
      "score": 0.9581
    }
  ],
  "provider": "gemini",
  "model": "gemini-3.6-flash",
  "latency_ms": 4662.2
}
```

### Response Schema Fields

- `answer`: Markdown-formatted response text with line-level citations.
- `sources`: Array of retrieved code attribution objects:
  - `repository`: Repository identifier string.
  - `file`: Base file name (e.g. `engine.ts`).
  - `symbol`: Extracted symbol name (function/class) or `null`.
  - `start_line`: 1-indexed starting line number.
  - `end_line`: 1-indexed ending line number.
  - `score`: Relevance similarity score ($[0.0, 1.0]$).
- `provider`: LLM provider name (`gemini`).
- `model`: Gemini model name (`gemini-3.6-flash`).
- `latency_ms`: Total execution processing latency in milliseconds.

### Status Codes & Error Responses

| Status Code | Description | Error Detail Example |
|---|---|---|
| `200 OK` | Query processed successfully | Answer, sources, and metadata |
| `400 Bad Request` | Unindexed repo or empty query | `{"detail": "No repository has been indexed yet."}` |
| `401 Unauthorized` | Missing or invalid API key | `{"detail": "Invalid or missing API key."}` |
| `502 Bad Gateway` | Gemini API or search failure | `{"detail": "Gemini API error (404): Model gemini-3.6-flash unavailable."}` |

### Example `curl` Request
```bash
curl -i -X POST http://localhost:8000/query \
  -H "X-API-Key: secret_key_123" \
  -H "Content-Type: application/json" \
  -d '{"query": "Where is VerificationEngine implemented?", "top_k": 5}'
```
