"use client";

import React, { useState, useRef, useEffect, useCallback } from "react";
import {
  Terminal,
  Cpu,
  Clock,
  Check,
  Copy,
  Sliders,
  Sparkles,
  ArrowUp,
  ArrowDown,
  AlertCircle,
  Bot,
  User,
  ShieldCheck,
} from "lucide-react";
import { QueryResponse, SourceDocument } from "@/lib/types";
import { MarkdownRenderer } from "./MarkdownRenderer";
import { SourceCardList } from "./SourceCardList";

export interface ConversationItem {
  query: string;
  response?: QueryResponse;
  error?: string;
}

interface ConversationViewProps {
  conversations: ConversationItem[];
  isLoading: boolean;
  onSendQuery: (query: string, topK: number) => void;
  onSelectEvidence: (sourceIndex: number, sources: SourceDocument[]) => void;
  selectedEvidenceIndex: number;
}

export function ConversationView({
  conversations,
  isLoading,
  onSendQuery,
  onSelectEvidence,
  selectedEvidenceIndex,
}: ConversationViewProps) {
  const [inputText, setInputText] = useState<string>("");
  const [topK, setTopK] = useState<number>(5);
  const [showTopK, setShowTopK] = useState<boolean>(false);
  const [copiedIndex, setCopiedIndex] = useState<number | null>(null);
  const [isUserScrolledUp, setIsUserScrolledUp] = useState<boolean>(false);

  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  /**
   * Smoothly scrolls the chat viewport to the very bottom.
   */
  const scrollToBottom = useCallback((behavior: ScrollBehavior = "smooth") => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior, block: "end" });
    }
  }, []);

  /**
   * Handle user manual scroll events to detect if the user scrolled up.
   */
  const handleScroll = () => {
    const el = scrollContainerRef.current;
    if (!el) return;

    const distanceFromBottom = el.scrollHeight - el.scrollTop - el.clientHeight;
    // If the user has scrolled up more than 90px from the bottom, pause auto-scroll
    const scrolledUp = distanceFromBottom > 90;
    setIsUserScrolledUp(scrolledUp);
  };

  // Auto-scroll when new messages arrive or loading begins, unless the user intentionally scrolled up
  useEffect(() => {
    if (!isUserScrolledUp) {
      scrollToBottom("smooth");
    }
  }, [conversations, isLoading, isUserScrolledUp, scrollToBottom]);

  // Initial scroll to bottom on mount
  useEffect(() => {
    scrollToBottom("auto");
  }, [scrollToBottom]);

  const handleSubmit = (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!inputText.trim() || isLoading) return;
    onSendQuery(inputText.trim(), topK);
    setInputText("");
    setIsUserScrolledUp(false);
    setTimeout(() => scrollToBottom("smooth"), 50);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if ((e.metaKey || e.ctrlKey) && e.key === "Enter") {
      e.preventDefault();
      handleSubmit();
    }
  };

  const handleCopy = (text: string, index: number) => {
    navigator.clipboard.writeText(text);
    setCopiedIndex(index);
    setTimeout(() => setCopiedIndex(null), 2000);
  };

  return (
    <div className="flex-1 flex flex-col h-full bg-[#111111] min-w-0 relative font-sans">
      {/* 1. Dedicated Scrollable Message Container */}
      <div
        ref={scrollContainerRef}
        onScroll={handleScroll}
        className="flex-1 min-h-0 overflow-y-auto overflow-x-hidden p-4 md:p-6 pb-8 scroll-smooth"
      >
        <div className="max-w-4xl mx-auto flex flex-col gap-6">
          {conversations.map((item, idx) => (
            <div key={idx} className="flex flex-col gap-5 animate-fade-in-up">
              {/* User Turn Card */}
              <div className="self-end max-w-[88%] md:max-w-[80%] flex items-start gap-2.5">
                <div className="bg-[#1E293B]/60 border border-[#334155]/70 rounded-2xl rounded-tr-xs p-4 shadow-sm text-sm text-[#f1f5f9] leading-relaxed">
                  <p className="whitespace-pre-wrap">{item.query}</p>
                </div>
                <div className="w-7 h-7 rounded-full bg-[#1e293b] border border-[#334155] text-[#93c5fd] shrink-0 flex items-center justify-center mt-1">
                  <User className="w-3.5 h-3.5" />
                </div>
              </div>

              {/* Assistant Turn Card */}
              {item.response ? (
                <div className="self-start w-full bg-[#161616] border border-[#2A2A2A] rounded-2xl rounded-tl-xs p-4 md:p-6 shadow-sm flex flex-col gap-4">
                  {/* Assistant Header Bar */}
                  <div className="flex items-center justify-between pb-3 border-b border-[#2A2A2A]/70 text-[11px] font-mono text-[#8c909f]">
                    <div className="flex items-center gap-2">
                      <div className="w-6 h-6 rounded-lg bg-[#304671]/40 border border-[#3B82F6]/40 text-[#adc6ff] flex items-center justify-center">
                        <Terminal className="w-3.5 h-3.5" />
                      </div>
                      <span className="font-semibold text-[#f5f5f5]">DevMind AI</span>
                      <span className="hidden sm:inline bg-[#1f293d] text-[#adc6ff] px-1.5 py-0.5 rounded border border-[#2e3b52] text-[10px]">
                        {item.response.model}
                      </span>
                    </div>

                    <div className="flex items-center gap-3">
                      <span className="flex items-center gap-1 text-amber-400/90">
                        <Clock className="w-3 h-3" />
                        <span>{Math.round(item.response.latency_ms)}ms</span>
                      </span>

                      <button
                        type="button"
                        onClick={() => handleCopy(item.response!.answer, idx)}
                        className="flex items-center gap-1 px-2 py-1 text-[#8c909f] hover:text-[#e2e2e2] hover:bg-[#252525] rounded transition-colors cursor-pointer"
                        title="Copy Markdown Answer"
                      >
                        {copiedIndex === idx ? (
                          <>
                            <Check className="w-3.5 h-3.5 text-[#10B981]" />
                            <span className="text-[#10B981] font-semibold">Copied</span>
                          </>
                        ) : (
                          <>
                            <Copy className="w-3.5 h-3.5" />
                            <span>Copy</span>
                          </>
                        )}
                      </button>
                    </div>
                  </div>

                  {/* Structured Answer Markdown Body */}
                  <div className="min-w-0">
                    <MarkdownRenderer
                      content={item.response.answer}
                      sources={item.response.sources}
                      onSelectSource={(sIdx) =>
                        onSelectEvidence(sIdx, item.response?.sources || [])
                      }
                    />
                  </div>

                  {/* Sources & Verified Code Evidence Section */}
                  {item.response.sources && item.response.sources.length > 0 && (
                    <SourceCardList
                      sources={item.response.sources}
                      selectedSourceIndex={selectedEvidenceIndex}
                      onSelectSource={(sIdx) =>
                        onSelectEvidence(sIdx, item.response?.sources || [])
                      }
                    />
                  )}
                </div>
              ) : item.error ? (
                /* Error Turn Card */
                <div className="self-start w-full p-4 rounded-xl bg-[#93000a]/20 border border-[#ffb4ab]/30 text-xs font-mono text-[#ffb4ab] flex items-start gap-2.5">
                  <AlertCircle className="w-4 h-4 shrink-0 text-[#ffb4ab] mt-0.5" />
                  <div>
                    <p className="font-semibold mb-1">Query Processing Failed</p>
                    <p className="opacity-90">{item.error}</p>
                  </div>
                </div>
              ) : null}
            </div>
          ))}

          {/* Assistant Generation / Loading State */}
          {isLoading && (
            <div className="self-start w-full max-w-2xl bg-[#161616] border border-[#2A2A2A] rounded-2xl rounded-tl-xs p-5 shadow-sm animate-pulse flex flex-col gap-3">
              <div className="flex items-center gap-2 text-xs font-mono text-[#adc6ff]">
                <div className="w-2.5 h-2.5 rounded-full bg-[#3B82F6] animate-ping" />
                <span className="font-semibold">DevMind AI is inspecting repository context...</span>
              </div>
              <div className="space-y-2 mt-1">
                <div className="h-3.5 bg-[#252525] rounded w-3/4" />
                <div className="h-3.5 bg-[#252525] rounded w-full" />
                <div className="h-3.5 bg-[#252525] rounded w-5/6" />
              </div>
            </div>
          )}

          {/* Invisible Anchor for Accurate Auto-Scroll */}
          <div ref={messagesEndRef} className="h-2" />
        </div>
      </div>

      {/* Floating "Jump to Latest" Pill (Appears when user scrolls up) */}
      {isUserScrolledUp && (
        <div className="absolute bottom-28 left-1/2 -translate-x-1/2 z-20 animate-fade-in-up">
          <button
            type="button"
            onClick={() => {
              setIsUserScrolledUp(false);
              scrollToBottom("smooth");
            }}
            className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-full bg-[#1e293b] hover:bg-[#2563eb] text-[#adc6ff] hover:text-white border border-[#3b82f6]/50 shadow-xl text-xs font-mono font-medium transition-all cursor-pointer backdrop-blur-md"
          >
            <ArrowDown className="w-3.5 h-3.5 animate-bounce" />
            <span>Jump to latest</span>
          </button>
        </div>
      )}

      {/* 2. Dedicated Composer Input Container (Siblings with scroll area, zero overlap) */}
      <div className="shrink-0 bg-[#111111] border-t border-[#2A2A2A] p-3 md:p-4 z-10">
        <div className="max-w-4xl mx-auto">
          <form
            onSubmit={handleSubmit}
            className="relative bg-[#171717] border border-[#2A2A2A] rounded-xl focus-within:border-[#3B82F6] transition-colors flex flex-col shadow-lg"
          >
            <textarea
              ref={textareaRef}
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              onKeyDown={handleKeyDown}
              disabled={isLoading}
              rows={2}
              placeholder="Ask anything about this codebase... (Cmd + Enter to submit)"
              className="w-full bg-transparent text-[#e2e2e2] text-sm p-3.5 resize-none focus:outline-none placeholder-[#8c909f] disabled:opacity-50"
            />

            <div className="flex items-center justify-between p-2 border-t border-[#2A2A2A] bg-[#1C1C1C] rounded-b-xl">
              {/* Top-K Control */}
              <div className="flex items-center gap-2 text-xs font-mono text-[#a1a1aa]">
                <button
                  type="button"
                  onClick={() => setShowTopK(!showTopK)}
                  className="flex items-center gap-1 px-2 py-1 rounded hover:bg-[#282a2b] text-[#8c909f] hover:text-[#e2e2e2] transition-colors cursor-pointer"
                  title="Configure Top-K retrieval count"
                >
                  <Sliders className="w-3.5 h-3.5 text-[#3B82F6]" />
                  <span>
                    top_k: <strong className="text-[#adc6ff]">{topK}</strong>
                  </span>
                </button>

                {showTopK && (
                  <div className="flex items-center gap-2 bg-[#121414] px-2.5 py-1 rounded border border-[#2A2A2A]">
                    <input
                      type="range"
                      min={1}
                      max={20}
                      value={topK}
                      onChange={(e) => setTopK(Number(e.target.value))}
                      className="w-20 accent-[#3B82F6] cursor-pointer"
                    />
                    <span className="text-[11px] text-[#adc6ff] w-4 font-bold">{topK}</span>
                  </div>
                )}
              </div>

              {/* Submit Button */}
              <button
                type="submit"
                disabled={!inputText.trim() || isLoading}
                className="bg-[#3B82F6] hover:bg-[#2563eb] text-white w-8 h-8 rounded-lg flex items-center justify-center transition-colors disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer shadow-sm"
                aria-label="Send Query"
              >
                <ArrowUp className="w-4 h-4" />
              </button>
            </div>
          </form>

          <div className="text-center mt-2">
            <span className="text-[11px] font-mono text-[#8c909f] flex items-center justify-center gap-1.5">
              <ShieldCheck className="w-3 h-3 text-[#10B981]" />
              <span>Grounded in verified AST chunks & pgvector embeddings</span>
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
