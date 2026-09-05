/**
 * @vitest-environment happy-dom
 */

import React, { act } from "react";
import { createRoot } from "react-dom/client";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { MarkdownRenderer } from "../components/MarkdownRenderer";
import { SourceCardList } from "../components/SourceCardList";
import { EvidencePanel } from "../components/EvidencePanel";
import { ConversationView } from "../components/ConversationView";
import { SourceDocument, QueryResponse } from "../lib/types";

// Configure React act environment for Happy DOM
(globalThis as any).IS_REACT_ACT_ENVIRONMENT = true;

describe("MarkdownRenderer Component", () => {
  let container: HTMLDivElement;

  beforeEach(() => {
    container = document.createElement("div");
    document.body.appendChild(container);
  });

  afterEach(() => {
    document.body.removeChild(container);
  });

  it("1. renders short AI response correctly", async () => {
    const root = createRoot(container);
    await act(async () => {
      root.render(<MarkdownRenderer content="ProofOS is a decentralized verification platform." />);
    });
    expect(container.textContent).toContain("ProofOS is a decentralized verification platform.");
  });

  it("2. renders long AI response with markdown headings, lists, bold, and quotes", async () => {
    const root = createRoot(container);
    const longContent = `
# System Architecture

ProofOS combines three core components:

## 1. Reputation Engine
- Calculates builder reputation scores
- Verifies Ed25519 signatures

## 2. API Routes
1. \`/api/verify\` - verification entry point
2. \`/api/sync\` - github aggregation

> Note: All verification flows run asynchronously.

| Metric | Target |
| :--- | :--- |
| Latency | < 300ms |
| Memory | 512 MB |
`;

    await act(async () => {
      root.render(<MarkdownRenderer content={longContent} />);
    });

    expect(container.querySelector("h1")?.textContent).toContain("System Architecture");
    expect(container.querySelector("h2")?.textContent).toContain("1. Reputation Engine");
    expect(container.querySelectorAll("li").length).toBe(4);
    expect(container.querySelector("blockquote")?.textContent).toContain("All verification flows run asynchronously.");
    expect(container.querySelector("table")).not.toBeNull();
    expect(container.textContent).toContain("Latency");
  });

  it("3. renders inline code badges and syntax highlighted code blocks with copy controls", async () => {
    const root = createRoot(container);
    const content = `
The function \`verifyCredentials()\` executes verification:

\`\`\`typescript
export async function verifyCredentials(id: string): Promise<boolean> {
  const result = await engine.verify(id);
  return result.isValid;
}
\`\`\`
`;

    await act(async () => {
      root.render(<MarkdownRenderer content={content} />);
    });

    expect(container.querySelector("code")?.textContent).toContain("verifyCredentials()");
    const pre = container.querySelector("pre");
    expect(pre).not.toBeNull();
    expect(pre?.textContent).toContain("export async function verifyCredentials");
    expect(container.textContent).toContain("typescript");
    expect(container.textContent).toContain("Copy");
  });

  it("4. resolves inline citations and bracketed citations [1] and fires onSelectSource callback on click", async () => {
    const root = createRoot(container);
    const onSelectSource = vi.fn();
    const mockSources: SourceDocument[] = [
      {
        repository: "proofos",
        file: "engine.ts",
        file_path: "lib/verification/engine.ts",
        symbol: "VerificationEngine",
        start_line: 89,
        end_line: 103,
        score: 0.92,
      },
    ];

    const content = "Scoring logic is detailed in [1] and `lib/verification/engine.ts:89-103`.";

    await act(async () => {
      root.render(
        <MarkdownRenderer
          content={content}
          sources={mockSources}
          onSelectSource={onSelectSource}
        />
      );
    });

    const buttons = container.querySelectorAll("button");
    expect(buttons.length).toBe(2);
    expect(buttons[0].textContent).toContain("[1]");
    expect(buttons[1].textContent).toContain("engine.ts");

    await act(async () => {
      buttons[0].click();
    });

    expect(onSelectSource).toHaveBeenCalledWith(0);
  });

  it("5. sanitizes dangerous markdown URLs and prevents script execution", async () => {
    const root = createRoot(container);
    const unsafeContent = `
[Safe Link](https://example.com)
[Dangerous Link](javascript:alert(1))
`;

    await act(async () => {
      root.render(<MarkdownRenderer content={unsafeContent} />);
    });

    const links = container.querySelectorAll("a");
    expect(links.length).toBe(1);
    expect(links[0].href).toBe("https://example.com/");
    expect(container.textContent).toContain("Dangerous Link");
  });
});

describe("SourceCardList Component", () => {
  let container: HTMLDivElement;

  beforeEach(() => {
    container = document.createElement("div");
    document.body.appendChild(container);
  });

  afterEach(() => {
    document.body.removeChild(container);
  });

  it("6. renders source cards with file path, line range, score badge, and snippet preview", async () => {
    const root = createRoot(container);
    const onSelectSource = vi.fn();
    const mockSources: SourceDocument[] = [
      {
        repository: "proofos",
        file: "engine.ts",
        file_path: "lib/verification/engine.ts",
        symbol: "VerificationEngine",
        start_line: 89,
        end_line: 103,
        score: 0.94,
        snippet: "export class VerificationEngine {\n  static computeScore() {}\n}",
      },
      {
        repository: "proofos",
        file: "scoring.ts",
        file_path: "lib/verification/scoring.ts",
        symbol: "ScoringService",
        start_line: 1,
        end_line: 25,
        score: 0.82,
      },
    ];

    await act(async () => {
      root.render(
        <SourceCardList
          sources={mockSources}
          selectedSourceIndex={0}
          onSelectSource={onSelectSource}
        />
      );
    });

    expect(container.textContent).toContain("Retrieved Code Evidence (2)");
    expect(container.textContent).toContain("engine.ts");
    expect(container.textContent).toContain("lib/verification/engine.ts");
    expect(container.textContent).toContain("L89–103");
    expect(container.textContent).toContain("94% match");
    expect(container.textContent).toContain("symbol:");
    expect(container.textContent).toContain("VerificationEngine");

    // Click to select source
    const cards = container.querySelectorAll(".group");
    await act(async () => {
      (cards[1] as HTMLElement).click();
    });
    expect(onSelectSource).toHaveBeenCalledWith(1);

    // Expand snippet preview
    const previewBtn = container.querySelector("button");
    await act(async () => {
      previewBtn?.click();
    });
    expect(container.textContent).toContain("export class VerificationEngine");
  });
});

describe("EvidencePanel Component", () => {
  let container: HTMLDivElement;

  beforeEach(() => {
    container = document.createElement("div");
    document.body.appendChild(container);
  });

  afterEach(() => {
    document.body.removeChild(container);
  });

  it("7. renders inspector header, line-numbered code viewer, and copy path controls", async () => {
    const root = createRoot(container);
    const onSelectSource = vi.fn();
    const onClose = vi.fn();
    const mockSources: SourceDocument[] = [
      {
        repository: "proofos",
        file: "engine.ts",
        file_path: "lib/verification/engine.ts",
        symbol: "VerificationEngine",
        start_line: 89,
        end_line: 91,
        score: 0.95,
        snippet: "line 89 code\nline 90 code\nline 91 code",
      },
    ];

    await act(async () => {
      root.render(
        <EvidencePanel
          sources={mockSources}
          selectedSourceIndex={0}
          onSelectSource={onSelectSource}
          onClose={onClose}
        />
      );
    });

    expect(container.textContent).toContain("Evidence Inspector");
    expect(container.textContent).toContain("engine.ts");
    expect(container.textContent).toContain("lib/verification/engine.ts");
    expect(container.textContent).toContain("Lines 89–91");
    expect(container.textContent).toContain("95% relevance");
    expect(container.textContent).toContain("89");
    expect(container.textContent).toContain("line 89 code");
  });
});

describe("ConversationView & Multi-Turn Evidence Isolation", () => {
  let container: HTMLDivElement;

  beforeEach(() => {
    container = document.createElement("div");
    document.body.appendChild(container);
    window.HTMLElement.prototype.scrollIntoView = vi.fn();
  });

  afterEach(() => {
    document.body.removeChild(container);
  });

  it("8. renders non-overlapping flex layout where messages and composer are dedicated siblings", async () => {
    const root = createRoot(container);
    const mockResponse: QueryResponse = {
      answer: "## Grounded Response\nFull verification architecture details.",
      sources: [
        {
          repository: "proofos",
          file: "engine.ts",
          file_path: "lib/verification/engine.ts",
          score: 0.95,
        },
      ],
      provider: "gemini",
      model: "gemini-3.6-flash",
      latency_ms: 180.2,
    };

    await act(async () => {
      root.render(
        <ConversationView
          conversations={[{ query: "Explain verification flow", response: mockResponse }]}
          isLoading={false}
          onSendQuery={vi.fn()}
          onSelectEvidence={vi.fn()}
          selectedEvidenceIndex={0}
        />
      );
    });

    // Verify messages scroll container has min-h-0 and overflow-y-auto
    const scrollArea = container.querySelector(".overflow-y-auto");
    expect(scrollArea).not.toBeNull();
    expect(scrollArea?.className).toContain("flex-1");
    expect(scrollArea?.className).toContain("min-h-0");

    // Verify composer container is shrink-0 sibling with textarea
    const composer = container.querySelector("form");
    expect(composer).not.toBeNull();
    expect(container.querySelector("textarea")).not.toBeNull();
  });

  it("9. passes turn-specific sources when clicking evidence on earlier turns", async () => {
    const root = createRoot(container);
    const onSelectEvidence = vi.fn();

    const turn1Sources: SourceDocument[] = [
      { repository: "proofos", file: "turn1.ts", file_path: "lib/turn1.ts", score: 0.9 },
    ];
    const turn2Sources: SourceDocument[] = [
      { repository: "proofos", file: "turn2.ts", file_path: "lib/turn2.ts", score: 0.85 },
    ];

    const conversations = [
      {
        query: "Query 1",
        response: {
          answer: "Answer 1",
          sources: turn1Sources,
          provider: "gemini",
          model: "gemini-3.6-flash",
          latency_ms: 100,
        },
      },
      {
        query: "Query 2",
        response: {
          answer: "Answer 2",
          sources: turn2Sources,
          provider: "gemini",
          model: "gemini-3.6-flash",
          latency_ms: 100,
        },
      },
    ];

    await act(async () => {
      root.render(
        <ConversationView
          conversations={conversations}
          isLoading={false}
          onSendQuery={vi.fn()}
          onSelectEvidence={onSelectEvidence}
          selectedEvidenceIndex={0}
        />
      );
    });

    // Find cards in turn 1
    const cards = container.querySelectorAll(".group");
    expect(cards.length).toBe(2);

    // Click card from Turn 1
    await act(async () => {
      (cards[0] as HTMLElement).click();
    });

    expect(onSelectEvidence).toHaveBeenCalledWith(0, turn1Sources);
  });
});
