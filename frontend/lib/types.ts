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
  job_id?: string | null;
  queue_position?: number | null;
}

export interface JobStatusResponse {
  job_id: string;
  repository_source: string;
  source_type: string;
  status: "QUEUED" | "RUNNING" | "COMPLETED" | "FAILED" | string;
  queue_position: number;
  result?: IndexRepositoryResponse | null;
  error?: string | null;
  created_at: number;
  updated_at: number;
}

export interface QueryRequest {
  query: string;
  top_k: number;
  conversation_id?: string | null;
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
  intent?: "GENERAL" | "REPOSITORY" | "MIXED" | string;
  conversation_id?: string | null;
}

export interface MessageItem {
  id: number;
  conversation_id: string;
  role: "user" | "assistant";
  content: string;
  intent?: string | null;
  sources?: SourceDocument[] | null;
  provider?: string | null;
  model?: string | null;
  latency_ms?: number | null;
  created_at: string;
}

export interface ConversationSummary {
  id: string;
  session_id: string;
  title: string;
  repository_name?: string | null;
  created_at: string;
  updated_at: string;
  message_count: number;
}

export interface ConversationDetail {
  id: string;
  session_id: string;
  title: string;
  repository_name?: string | null;
  created_at: string;
  updated_at: string;
  messages: MessageItem[];
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
