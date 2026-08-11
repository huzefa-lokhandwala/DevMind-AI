/**
 * @vitest-environment happy-dom
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import {
  getStoredApiKey,
  setStoredApiKey,
  clearStoredApiKey,
  getMaskedApiKey,
  checkHealth,
  checkReadiness,
  queryCodebase,
  indexRepository,
  AuthError,
  ValidationError,
} from "../lib/api-client";

describe("API Client & LocalStorage Auth Management", () => {
  beforeEach(() => {
    localStorage.clear();
    vi.restoreAllMocks();
  });

  it("persists and reads API key in localStorage under devmind_api_key", () => {
    expect(getStoredApiKey()).toBe("");
    setStoredApiKey("test_secret_key_123");
    expect(getStoredApiKey()).toBe("test_secret_key_123");
    expect(localStorage.getItem("devmind_api_key")).toBe("test_secret_key_123");
  });

  it("clears API key from localStorage", () => {
    setStoredApiKey("test_secret_key_123");
    clearStoredApiKey();
    expect(getStoredApiKey()).toBe("");
    expect(localStorage.getItem("devmind_api_key")).toBeNull();
  });

  it("masks API key correctly for UI display", () => {
    expect(getMaskedApiKey("")).toBe("");
    expect(getMaskedApiKey("abcd")).toBe("••••");
    expect(getMaskedApiKey("my_devmind_secret_9999")).toBe("••••••••9999");
  });
});

describe("API Client HTTP Request Handlers", () => {
  beforeEach(() => {
    localStorage.clear();
    vi.restoreAllMocks();
  });

  it("checkHealth calls GET /health without auth headers", async () => {
    const mockHealth = { status: "ok", service: "DevMind AI" };
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => mockHealth,
    });

    const res = await checkHealth();
    expect(res).toEqual(mockHealth);
    expect(globalThis.fetch).toHaveBeenCalledWith(
      "http://localhost:8000/health",
      expect.objectContaining({
        method: "GET",
      })
    );
  });

  it("checkReadiness calls GET /health/ready", async () => {
    const mockReadiness = { status: "ready", database: "connected", service: "DevMind AI" };
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => mockReadiness,
    });

    const res = await checkReadiness();
    expect(res).toEqual(mockReadiness);
  });

  it("queryCodebase includes X-API-Key header when configured", async () => {
    setStoredApiKey("secret_key_456");

    const mockResponse = {
      answer: "Test answer",
      sources: [
        {
          repository: "proofos",
          file: "engine.ts",
          symbol: "VerificationEngine",
          start_line: 13,
          end_line: 156,
          score: 0.95,
        },
      ],
      provider: "gemini",
      model: "gemini-3.6-flash",
      latency_ms: 120.5,
    };

    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => mockResponse,
    });

    const res = await queryCodebase({ query: "Where is VerificationEngine?", top_k: 5 });

    expect(res).toEqual(mockResponse);
    expect(globalThis.fetch).toHaveBeenCalledWith(
      "http://localhost:8000/query",
      expect.objectContaining({
        method: "POST",
        headers: expect.objectContaining({
          "X-API-Key": "secret_key_456",
        }),
      })
    );
  });

  it("throws AuthError on 401 Unauthorized response", async () => {
    setStoredApiKey("bad_key");

    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 401,
      json: async () => ({ detail: "Invalid or missing API key." }),
    });

    await expect(queryCodebase({ query: "Where is main?", top_k: 5 })).rejects.toThrow(AuthError);
  });

  it("indexRepository posts GitHub URL and parses IndexRepositoryResponse", async () => {
    setStoredApiKey("secret_key_456");

    const mockIndexRes = {
      repository: "proofos",
      files_loaded: 40,
      chunks_created: 40,
      embeddings_created: 40,
      status: "indexed",
    };

    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => mockIndexRes,
    });

    const res = await indexRepository({ github_url: "https://github.com/huzefa-lokhandwala/proofos" });
    expect(res).toEqual(mockIndexRes);
  });
});
