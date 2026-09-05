/**
 * Dedicated, typed API Client for DevMind AI FastAPI backend.
 * Handles API Base URL, X-API-Key headers, X-Session-ID isolation,
 * response parsing, and structured error boundaries.
 */

import {
  ConversationDetail,
  ConversationSummary,
  HealthStatus,
  IndexRepositoryRequest,
  IndexRepositoryResponse,
  JobStatusResponse,
  QueryRequest,
  QueryResponse,
  ReadinessStatus,
} from "./types";

const STORAGE_KEY_API_KEY = "devmind_api_key";
const STORAGE_KEY_SESSION_ID = "devmind_session_id";
const DEFAULT_API_BASE_URL = "http://localhost:8000";

export class ApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

export class AuthError extends ApiError {
  constructor(message = "Your DevMind API key is missing or invalid.") {
    super(message, 401);
    this.name = "AuthError";
  }
}

export class ValidationError extends ApiError {
  constructor(message = "The request was rejected by the backend. Check the inputs.") {
    super(message, 422);
    this.name = "ValidationError";
  }
}

export class RateLimitError extends ApiError {
  constructor(message = "Rate limit reached. Please wait and try again.") {
    super(message, 429);
    this.name = "RateLimitError";
  }
}

export class ServerError extends ApiError {
  constructor(message = "DevMind encountered a server error. Check the backend logs.") {
    super(message, 500);
    this.name = "ServerError";
  }
}

export class NetworkError extends ApiError {
  constructor(message = "Unable to reach the DevMind backend.") {
    super(message, 0);
    this.name = "NetworkError";
  }
}

/**
 * Get API Base URL from NEXT_PUBLIC_API_BASE_URL or default to http://localhost:8000.
 */
export function getApiBaseUrl(): string {
  return process.env.NEXT_PUBLIC_API_BASE_URL || DEFAULT_API_BASE_URL;
}

/**
 * Read API Key safely from browser localStorage.
 */
export function getStoredApiKey(): string {
  if (typeof window === "undefined") {
    return "";
  }
  return localStorage.getItem(STORAGE_KEY_API_KEY) || "";
}

/**
 * Persist API Key in browser localStorage.
 */
export function setStoredApiKey(key: string): void {
  if (typeof window === "undefined") {
    return;
  }
  if (!key.trim()) {
    localStorage.removeItem(STORAGE_KEY_API_KEY);
  } else {
    localStorage.setItem(STORAGE_KEY_API_KEY, key.trim());
  }
}

/**
 * Remove stored API Key from browser localStorage.
 */
export function clearStoredApiKey(): void {
  if (typeof window !== "undefined") {
    localStorage.removeItem(STORAGE_KEY_API_KEY);
  }
}

/**
 * Get masked representation of API Key for display (e.g. ••••••••abcd).
 */
export function getMaskedApiKey(key: string): string {
  if (!key) return "";
  if (key.length <= 4) return "••••";
  return "••••••••" + key.slice(-4);
}

/**
 * Get or create stable anonymous browser session ID in localStorage.
 */
export function getOrCreateSessionId(): string {
  if (typeof window === "undefined") {
    return "server-session";
  }
  let sessionId = localStorage.getItem(STORAGE_KEY_SESSION_ID);
  if (!sessionId) {
    sessionId = typeof crypto !== "undefined" && crypto.randomUUID ? crypto.randomUUID() : "sess-" + Math.random().toString(36).slice(2, 11);
    localStorage.setItem(STORAGE_KEY_SESSION_ID, sessionId);
  }
  return sessionId;
}

/**
 * Internal helper for fetching with headers, error translation, and network handling.
 */
async function fetchApi<T>(
  endpoint: string,
  options: RequestInit = {},
  requiresAuth = true
): Promise<T> {
  const baseUrl = getApiBaseUrl();
  const url = `${baseUrl.replace(/\/+$/, "")}${endpoint}`;

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    Accept: "application/json",
    "X-Session-ID": getOrCreateSessionId(),
    ...(options.headers as Record<string, string>),
  };

  if (requiresAuth) {
    const apiKey = getStoredApiKey();
    if (apiKey) {
      headers["X-API-Key"] = apiKey;
    }
  }

  try {
    const response = await fetch(url, {
      ...options,
      headers,
    });

    if (response.ok) {
      if (response.status === 204) {
        return {} as T;
      }
      return (await response.json()) as T;
    }

    // Handle non-2xx response statuses
    let detailMsg = "";
    try {
      const errData = await response.json();
      detailMsg = typeof errData.detail === "string" ? errData.detail : JSON.stringify(errData.detail);
    } catch {
      detailMsg = response.statusText;
    }

    if (response.status === 401) {
      throw new AuthError(detailMsg || "Your DevMind API key is missing or invalid.");
    }
    if (response.status === 400 || response.status === 422) {
      throw new ValidationError(detailMsg || "The request was rejected by the backend. Check the inputs.");
    }
    if (response.status === 429) {
      throw new RateLimitError(detailMsg || "Rate limit reached. Please wait and try again.");
    }
    if (response.status >= 500) {
      throw new ServerError(detailMsg || "DevMind encountered a server error. Check the backend logs.");
    }

    throw new ApiError(detailMsg || `Request failed with status ${response.status}`, response.status);
  } catch (err: any) {
    if (err instanceof ApiError) {
      throw err;
    }
    throw new NetworkError("Unable to reach the DevMind backend.");
  }
}

/**
 * Check system identification health (Public endpoint).
 */
export async function checkHealth(): Promise<HealthStatus> {
  return fetchApi<HealthStatus>("/health", { method: "GET" }, false);
}

/**
 * Check system and database readiness status (Public endpoint).
 */
export async function checkReadiness(): Promise<ReadinessStatus> {
  return fetchApi<ReadinessStatus>("/health/ready", { method: "GET" }, false);
}

/**
 * Index a repository (GitHub URL or Local Path) (Protected endpoint).
 */
export async function indexRepository(
  payload: IndexRepositoryRequest
): Promise<IndexRepositoryResponse> {
  return fetchApi<IndexRepositoryResponse>(
    "/repositories/index",
    {
      method: "POST",
      body: JSON.stringify(payload),
    },
    true
  );
}

/**
 * Check asynchronous status and queue position of an indexing job (Protected endpoint).
 */
export async function getIndexingStatus(jobId: string): Promise<JobStatusResponse> {
  return fetchApi<JobStatusResponse>(`/repositories/index/status/${jobId}`, { method: "GET" }, true);
}

/**
 * Query the indexed codebase with natural language and intent routing (Protected endpoint).
 */
export async function queryCodebase(payload: QueryRequest): Promise<QueryResponse> {
  return fetchApi<QueryResponse>(
    "/query",
    {
      method: "POST",
      body: JSON.stringify(payload),
    },
    true
  );
}

/**
 * List all persistent conversations for the current session.
 */
export async function listConversations(): Promise<ConversationSummary[]> {
  return fetchApi<ConversationSummary[]>("/conversations", { method: "GET" }, true);
}

/**
 * Create a new conversation.
 */
export async function createConversation(
  title = "New Chat",
  repository_name?: string | null
): Promise<ConversationDetail> {
  return fetchApi<ConversationDetail>(
    "/conversations",
    {
      method: "POST",
      body: JSON.stringify({ title, repository_name }),
    },
    true
  );
}

/**
 * Get full conversation history by conversation ID.
 */
export async function getConversation(conversationId: string): Promise<ConversationDetail> {
  return fetchApi<ConversationDetail>(`/conversations/${conversationId}`, { method: "GET" }, true);
}

/**
 * Delete a specific conversation by ID.
 */
export async function deleteConversation(conversationId: string): Promise<void> {
  return fetchApi<void>(`/conversations/${conversationId}`, { method: "DELETE" }, true);
}

/**
 * Clear all conversations for the current session.
 */
export async function clearAllConversations(): Promise<void> {
  return fetchApi<void>("/conversations", { method: "DELETE" }, true);
}
