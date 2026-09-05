/**
 * TypeScript interfaces synchronized with DevMind AI FastAPI Pydantic schemas.
 */

export interface HealthStatus {
  status: string;
  service: string;
}

export interface ReadinessStatus {
  status: string;
  database: string;
  service: string;
}

export interface IndexRepositoryRequest {
  repository_path?: string;
  github_url?: string;
}

export interface IndexRepositoryResponse {
  repository: string;
  files_loaded: number;
  chunks_created: number;
  embeddings_created: number;
  status: string;
}

export interface QueryRequest {
  query: string;
  top_k: number;
}

export interface SourceDocument {
  repository: string;
  file: string;
  file_path?: string | null;
  symbol?: string | null;
  start_line?: number | null;
  end_line?: number | null;
  score: number;
  snippet?: string | null;
  language?: string | null;
}

export interface QueryResponse {
  answer: string;
  sources: SourceDocument[];
  provider: string;
  model: string;
  latency_ms: number;
}

export interface ApiErrorResponse {
  detail: string | { [key: string]: any };
}

export interface QueryHistoryItem {
  id: string;
  query: string;
  top_k: number;
  timestamp: string;
  response?: QueryResponse;
  error?: string;
}
