"use client";

import React, { useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Check, Copy, Code, FileText, ExternalLink } from "lucide-react";
import { SourceDocument } from "@/lib/types";

interface MarkdownRendererProps {
  content: string;
  sources?: SourceDocument[];
  onSelectSource?: (index: number) => void;
}

export function MarkdownRenderer({
  content,
  sources = [],
  onSelectSource,
}: MarkdownRendererProps) {
  const [copiedBlockId, setCopiedBlockId] = useState<string | null>(null);

  const handleCopyCode = (codeText: string, blockId: string) => {
    navigator.clipboard.writeText(codeText);
    setCopiedBlockId(blockId);
    setTimeout(() => setCopiedBlockId(null), 2000);
  };

  /**
   * Safe URL scheme validator for markdown links.
   */
  const sanitizeUrl = (url?: string): string | undefined => {
    if (!url) return undefined;
    const clean = url.trim().toLowerCase();
    if (
      clean.startsWith("http://") ||
      clean.startsWith("https://") ||
      clean.startsWith("#") ||
      clean.startsWith("mailto:")
    ) {
      return url;
    }
    return undefined; // Blocks javascript:, data:, vbscript:, etc.
  };

  /**
   * Helper to match an inline token to a retrieved SourceDocument.
   * Priority:
   * 1. Numeric index [N] or N
   * 2. Full file_path match (case-insensitive)
   * 3. Basename match
   */
  const findMatchingSourceIndex = (token: string): number => {
    if (!sources || sources.length === 0) return -1;
    const clean = token.trim().replace(/^[`'"]+|[`'"]+$/g, "");

    // 1. Match bracketed numeric citation e.g. "[1]" or "1"
    const numMatch = clean.match(/^\[?(\d+)\]?$/);
    if (numMatch) {
      const idx = parseInt(numMatch[1], 10) - 1;
      if (idx >= 0 && idx < sources.length) return idx;
    }

    // 2. Extract path without line numbers e.g. "lib/verification/engine.ts:89-103" -> "lib/verification/engine.ts"
    const rawPath = clean.split(":")[0].trim().toLowerCase();
    if (rawPath) {
      // 2a. Match full file_path if available
      const fullPathIdx = sources.findIndex(
        (s) => s.file_path && s.file_path.toLowerCase() === rawPath
      );
      if (fullPathIdx !== -1) return fullPathIdx;

      // 2b. Match endsWith for partial paths
      const endsWithIdx = sources.findIndex(
        (s) => s.file_path && s.file_path.toLowerCase().endsWith(rawPath)
      );
      if (endsWithIdx !== -1) return endsWithIdx;

      // 2c. Match basename
      const fileOnly = rawPath.split("/").pop();
      if (fileOnly) {
        const baseIdx = sources.findIndex((s) => {
          const sFile = s.file.toLowerCase();
          const sPath = s.file_path?.toLowerCase() || "";
          return sFile === fileOnly || sPath.endsWith("/" + fileOnly) || sPath === fileOnly;
        });
        if (baseIdx !== -1) return baseIdx;
      }
    }

    return -1;
  };

  /**
   * Helper to parse string text and render bracketed citations like [1], [2], [1][2] as interactive pills.
   */
  const renderTextWithCitations = (text: string) => {
    if (!sources || sources.length === 0 || !onSelectSource) {
      return text;
    }

    // Regex to split on [1], [2], etc.
    const citationRegex = /(\[\d+\])/g;
    const parts = text.split(citationRegex);

    if (parts.length === 1) {
      return text;
    }

    return parts.map((part, pIdx) => {
      const match = part.match(/^\[(\d+)\]$/);
      if (match) {
        const sourceIndex = parseInt(match[1], 10) - 1;
        if (sourceIndex >= 0 && sourceIndex < sources.length) {
          const src = sources[sourceIndex];
          const fileName = src.file.split("/").pop() || src.file;
          return (
            <button
              key={pIdx}
              type="button"
              onClick={() => onSelectSource(sourceIndex)}
              className="inline-flex items-center gap-1 mx-0.5 px-1.5 py-0.2 rounded text-[11px] font-mono font-medium bg-[#1e293b] text-[#93c5fd] hover:bg-[#2563eb] hover:text-white border border-[#3b82f6]/40 transition-all cursor-pointer shadow-xs align-baseline"
              title={`Inspect ${src.file_path || src.file} in Evidence Inspector`}
            >
              <span>[{sourceIndex + 1}]</span>
              <span className="hidden sm:inline opacity-90">{fileName}</span>
            </button>
          );
        }
      }
      return <React.Fragment key={pIdx}>{part}</React.Fragment>;
    });
  };

  return (
    <div className="markdown-content text-[#e2e2e2] text-sm leading-relaxed space-y-3 font-sans break-words select-text">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          h1: ({ children }) => (
            <h1 className="text-lg font-bold text-[#f5f5f5] mt-5 mb-2.5 pb-1.5 border-b border-[#2A2A2A] flex items-center gap-2">
              {children}
            </h1>
          ),
          h2: ({ children }) => (
            <h2 className="text-base font-semibold text-[#adc6ff] mt-4 mb-2 flex items-center gap-2">
              {children}
            </h2>
          ),
          h3: ({ children }) => (
            <h3 className="text-sm font-semibold text-[#e2e2e2] mt-3.5 mb-1.5">
              {children}
            </h3>
          ),
          h4: ({ children }) => (
            <h4 className="text-xs font-semibold text-[#adc6ff] uppercase tracking-wider mt-3 mb-1">
              {children}
            </h4>
          ),
          p: ({ children }) => {
            // Process child text strings for bracketed citations
            const processedChildren = React.Children.map(children, (child) => {
              if (typeof child === "string") {
                return renderTextWithCitations(child);
              }
              return child;
            });

            return (
              <p className="mb-3 text-[#d4d4d8] leading-relaxed last:mb-0">
                {processedChildren}
              </p>
            );
          },
          ul: ({ children }) => (
            <ul className="list-disc list-outside ml-5 mb-3 space-y-1.5 text-[#d4d4d8]">
              {children}
            </ul>
          ),
          ol: ({ children }) => (
            <ol className="list-decimal list-outside ml-5 mb-3 space-y-1.5 text-[#d4d4d8]">
              {children}
            </ol>
          ),
          li: ({ children }) => {
            const processedChildren = React.Children.map(children, (child) => {
              if (typeof child === "string") {
                return renderTextWithCitations(child);
              }
              return child;
            });
            return <li className="leading-relaxed">{processedChildren}</li>;
          },
          strong: ({ children }) => (
            <strong className="font-semibold text-white">{children}</strong>
          ),
          em: ({ children }) => (
            <em className="italic text-[#cbd5e1]">{children}</em>
          ),
          blockquote: ({ children }) => (
            <blockquote className="border-l-2 border-[#3B82F6] bg-[#1E293B]/40 px-3.5 py-2.5 rounded-r my-3 text-xs text-[#cbd5e1] space-y-1">
              {children}
            </blockquote>
          ),
          a: ({ href, children }) => {
            const safeHref = sanitizeUrl(href);
            if (!safeHref) {
              return <span className="text-[#93c5fd] underline">{children}</span>;
            }
            return (
              <a
                href={safeHref}
                target="_blank"
                rel="noopener noreferrer"
                className="text-[#93c5fd] hover:text-[#adc6ff] underline inline-flex items-center gap-0.5"
              >
                <span>{children}</span>
                <ExternalLink className="w-2.5 h-2.5 opacity-70" />
              </a>
            );
          },
          hr: () => <hr className="border-[#2A2A2A] my-4" />,
          table: ({ children }) => (
            <div className="overflow-x-auto my-3 border border-[#2A2A2A] rounded-lg shadow-sm">
              <table className="w-full text-left text-xs border-collapse divide-y divide-[#2A2A2A]">
                {children}
              </table>
            </div>
          ),
          thead: ({ children }) => (
            <thead className="bg-[#1C1C1C] text-[#adc6ff] font-mono text-[11px] uppercase tracking-wider">
              {children}
            </thead>
          ),
          tbody: ({ children }) => (
            <tbody className="divide-y divide-[#2A2A2A]/60 bg-[#121414] text-[#d4d4d8]">
              {children}
            </tbody>
          ),
          tr: ({ children }) => (
            <tr className="hover:bg-[#1C1C1C]/40 transition-colors">
              {children}
            </tr>
          ),
          th: ({ children }) => (
            <th className="px-3.5 py-2 font-semibold">{children}</th>
          ),
          td: ({ children }) => (
            <td className="px-3.5 py-2 whitespace-normal">{children}</td>
          ),
          code: ({ node, inline, className, children, ...props }: any) => {
            const codeString = String(children).replace(/\n$/, "");
            const matchLang = /language-(\w+)/.exec(className || "");
            const isBlock = !inline && (Boolean(matchLang) || codeString.includes("\n"));

            if (isBlock) {
              const blockId = `code-${Math.random().toString(36).substring(2, 9)}`;
              const langLabel = matchLang ? matchLang[1] : "code";

              return (
                <div className="relative my-3 rounded-lg overflow-hidden border border-[#2A2A2A] bg-[#0d1117] shadow-sm font-mono text-xs group">
                  <div className="flex items-center justify-between px-3.5 py-1.5 bg-[#161b22] border-b border-[#2A2A2A] text-[#8c909f]">
                    <span className="text-[11px] uppercase tracking-wider text-[#adc6ff] font-semibold flex items-center gap-1.5">
                      <Code className="w-3.5 h-3.5 text-[#3B82F6]" />
                      {langLabel}
                    </span>
                    <button
                      type="button"
                      onClick={() => handleCopyCode(codeString, blockId)}
                      className="flex items-center gap-1 text-[11px] text-[#8c909f] hover:text-[#e2e2e2] transition-colors px-1.5 py-0.5 rounded hover:bg-[#21262d] cursor-pointer"
                      title="Copy code snippet"
                    >
                      {copiedBlockId === blockId ? (
                        <>
                          <Check className="w-3 h-3 text-[#10B981]" />
                          <span className="text-[#10B981]">Copied</span>
                        </>
                      ) : (
                        <>
                          <Copy className="w-3 h-3" />
                          <span>Copy</span>
                        </>
                      )}
                    </button>
                  </div>
                  <pre className="p-3.5 overflow-x-auto text-[#e6edf3] leading-relaxed">
                    <code>{codeString}</code>
                  </pre>
                </div>
              );
            }

            // Inline code: check for citation resolution
            const matchedIndex = findMatchingSourceIndex(codeString);
            if (matchedIndex !== -1 && onSelectSource) {
              const src = sources[matchedIndex];
              const fileBasename = src.file.split("/").pop();
              return (
                <button
                  type="button"
                  onClick={() => onSelectSource(matchedIndex)}
                  className="inline-flex items-center gap-1 mx-0.5 px-1.5 py-0.5 rounded text-[11px] font-mono font-medium bg-[#1e293b] text-[#93c5fd] hover:bg-[#2563eb] hover:text-white border border-[#3b82f6]/40 transition-all cursor-pointer shadow-xs align-baseline"
                  title={`Click to inspect evidence in ${src.file_path || src.file}`}
                >
                  <FileText className="w-2.5 h-2.5" />
                  <span>[{matchedIndex + 1}] {fileBasename}</span>
                  {src.start_line && src.end_line && (
                    <span className="opacity-80 text-[10px]">:{src.start_line}-{src.end_line}</span>
                  )}
                </button>
              );
            }

            return (
              <code
                className="font-mono text-[12px] bg-[#1C1C1C] text-[#adc6ff] px-1.5 py-0.5 rounded border border-[#2A2A2A] mx-0.5"
                {...props}
              >
                {children}
              </code>
            );
          },
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}
