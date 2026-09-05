/**
 * @vitest-environment happy-dom
 */

import React, { act } from "react";
import { createRoot } from "react-dom/client";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { ConversationView } from "../components/ConversationView";
import { Sidebar } from "../components/Sidebar";
import { IndexModal } from "../components/IndexModal";
import { QueryResponse, SourceDocument, ConversationSummary } from "../lib/types";

(globalThis as any).IS_REACT_ACT_ENVIRONMENT = true;

describe("Query Intent and Evidence Proportionality UX", () => {
  let container: HTMLDivElement;

  beforeEach(() => {
    container = document.createElement("div");
    document.body.appendChild(container);
  });

  afterEach(() => {
    document.body.removeChild(container);
  });

  it("renders answer only for GENERAL queries with no sources and does NOT render Retrieved Code Evidence", async () => {
    const root = createRoot(container);
    const generalResponse: QueryResponse = {
      answer: "Dependency injection is a design pattern where an object receives its dependencies from external sources.",
      sources: [],
      provider: "gemini",
      model: "gemini-3.6-flash",
      latency_ms: 85,
      intent: "GENERAL",
    };

    const conversations = [
      {
        query: "What is DI?",
        response: generalResponse,
      },
    ];

    await act(async () => {
      root.render(
        <ConversationView
          conversations={conversations}
          isLoading={false}
          onSendQuery={() => {}}
          onSelectEvidence={() => {}}
          selectedEvidenceIndex={0}
        />
      );
    });

    expect(container.textContent).toContain("Dependency injection is a design pattern");
    expect(container.textContent).not.toContain("RETRIEVED CODE EVIDENCE");
  });

  it("renders RETRIEVED CODE EVIDENCE for REPOSITORY queries containing sources", async () => {
    const root = createRoot(container);
    const sampleSources: SourceDocument[] = [
      {
        repository: "proofos",
        file: "auth.py",
        file_path: "app/api/auth.py",
        symbol: "verify_api_key",
        start_line: 10,
        end_line: 30,
        score: 0.94,
        snippet: "def verify_api_key(api_key: str): ...",
        language: "python",
      },
    ];

    const repoResponse: QueryResponse = {
      answer: "Authentication is handled in `app/api/auth.py`.",
      sources: sampleSources,
      provider: "gemini",
      model: "gemini-3.6-flash",
      latency_ms: 140,
      intent: "REPOSITORY",
    };

    const conversations = [
      {
        query: "where is authentication implemented?",
        response: repoResponse,
      },
    ];

    await act(async () => {
      root.render(
        <ConversationView
          conversations={conversations}
          isLoading={false}
          onSendQuery={() => {}}
          onSelectEvidence={() => {}}
          selectedEvidenceIndex={0}
        />
      );
    });

    expect(container.textContent).toContain("Authentication is handled in");
    expect(container.textContent).toContain("Retrieved Code Evidence");
    expect(container.textContent).toContain("app/api/auth.py");
  });
});

describe("Sidebar Recent Conversations UX", () => {
  let container: HTMLDivElement;

  beforeEach(() => {
    container = document.createElement("div");
    document.body.appendChild(container);
  });

  afterEach(() => {
    document.body.removeChild(container);
  });

  it("renders list of recent conversations and handles selection", async () => {
    const root = createRoot(container);
    const mockConversations: ConversationSummary[] = [
      {
        id: "conv-1",
        session_id: "sess-1",
        title: "Authentication Implementation",
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        message_count: 2,
      },
      {
        id: "conv-2",
        session_id: "sess-1",
        title: "SORTTracker Overview",
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        message_count: 4,
      },
    ];

    const onSelect = vi.fn();
    const onDelete = vi.fn();

    await act(async () => {
      root.render(
        <Sidebar
          activeRepository="proofos"
          activeView="chat"
          conversations={mockConversations}
          activeConversationId="conv-1"
          onNewChat={() => {}}
          onSelectConversation={onSelect}
          onDeleteConversation={onDelete}
          onOpenIndexModal={() => {}}
          onOpenSettingsModal={() => {}}
          onToggleHistory={() => {}}
        />
      );
    });

    expect(container.textContent).toContain("Authentication Implementation");
    expect(container.textContent).toContain("SORTTracker Overview");

    // Click on second conversation
    const conv2El = Array.from(container.querySelectorAll("span")).find(
      (el) => el.textContent === "SORTTracker Overview"
    );
    expect(conv2El).toBeDefined();
    await act(async () => {
      conv2El?.parentElement?.parentElement?.dispatchEvent(
        new MouseEvent("click", { bubbles: true })
      );
    });
    expect(onSelect).toHaveBeenCalledWith("conv-2");
  });
});

describe("IndexModal Queue and Indeterminate Progress UX", () => {
  let container: HTMLDivElement;

  beforeEach(() => {
    container = document.createElement("div");
    document.body.appendChild(container);
  });

  afterEach(() => {
    document.body.removeChild(container);
  });

  it("renders closed modal as null", async () => {
    const root = createRoot(container);
    await act(async () => {
      root.render(
        <IndexModal
          isOpen={false}
          onClose={() => {}}
          onSuccess={() => {}}
          onAuthRequired={() => {}}
        />
      );
    });
    expect(container.textContent).toBe("");
  });

  it("renders form inputs when opened", async () => {
    const root = createRoot(container);
    await act(async () => {
      root.render(
        <IndexModal
          isOpen={true}
          onClose={() => {}}
          onSuccess={() => {}}
          onAuthRequired={() => {}}
        />
      );
    });

    expect(container.textContent).toContain("Index Repository");
    expect(container.textContent).toContain("GitHub Repository");
    expect(container.textContent).toContain("Local Path");
  });
});
