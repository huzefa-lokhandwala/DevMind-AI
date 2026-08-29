"use client";

import { useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import {
  Terminal,
  Cpu,
  Clock,
  Check,
  Copy,
  Code,
  Send,
  Sliders,
  Sparkles,
  Layers,
  ArrowUp,
} from "lucide-react";
import { QueryResponse, SourceDocument } from "@/lib/types";

interface ConversationItem {
  query: string;
  response?: QueryResponse;
  error?: string;
}

interface ConversationViewProps {
  conversations: ConversationItem[];
  isLoading: boolean;
  onSendQuery: (query: string, topK: number) => void;
  onSelectEvidence: (sourceIndex: number) => void;
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

  const handleSubmit = (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!inputText.trim() || isLoading) return;
    onSendQuery(inputText.trim(), topK);
    setInputText("");
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
      {/* Conversation Scroll Area */}
      <div className="flex-1 overflow-y-auto p-4 md:p-6 pb-[140px]">
        <div className="max-w-3xl mx-auto flex flex-col gap-6">
          {conversations.map((item, idx) => (
            <div key={idx} className="flex flex-col gap-5 animate-fade-in-up">
              {/* User Message Bubble */}
              <div className="self-end max-w-[85%] bg-[#1C1C1C] border border-[#2A2A2A] rounded-xl rounded-tr-sm p-4 shadow-sm">
                <p className="text-[#e2e2e2] text-sm leading-relaxed">{item.query}</p>
              </div>

              {/* AI Response Block */}
              {item.response ? (
                <div className="self-start max-w-full flex gap-3.5">
                  <div className="w-8 h-8 rounded-full bg-[#1C1C1C] border border-[#2A2A2A] text-[#adc6ff] shrink-0 flex items-center justify-center mt-1 shadow-sm">
                    <Terminal className="w-4 h-4" />
                  </div>

                  <div className="flex-1 min-w-0">
                    <div className="prose prose-invert max-w-none text-sm text-[#e2e2e2] leading-relaxed prose-pre:bg-[#121414] prose-pre:border prose-pre:border-[#2A2A2A] prose-code:font-mono prose-code:text-[#adc6ff] prose-code:bg-[#1C1C1C] prose-code:px-1 prose-code:py-0.5 prose-code:rounded">
                      <ReactMarkdown remarkPlugins={[remarkGfm]}>
                        {item.response.answer}
                      </ReactMarkdown>
                    </div>

                    {/* Sources Badge Row */}
                    {item.response.sources && item.response.sources.length > 0 && (
                      <div className="mt-4 pt-3 border-t border-[#2A2A2A]/80 flex flex-wrap items-center gap-2">
                        <span className="text-[11px] font-mono text-[#8c909f] uppercase tracking-wider flex items-center gap-1 mr-1">
                          <Layers className="w-3.5 h-3.5" />
                          <span>Sources:</span>
                        </span>
                        {item.response.sources.map((src, sIdx) => {
                          const isSelected = sIdx === selectedEvidenceIndex;
                          return (
                            <button
                              key={sIdx}
                              onClick={() => onSelectEvidence(sIdx)}
                              className={`flex items-center gap-1.5 px-2.5 py-1 rounded text-xs font-mono transition-all cursor-pointer ${
                                isSelected
                                  ? "bg-[#304671] text-[#adc6ff] border border-[#3B82F6]/60 shadow-sm"
                                  : "bg-[#1C1C1C] text-[#a1a1aa] hover:text-[#e2e2e2] hover:bg-[#282a2b] border border-[#2A2A2A]"
                              }`}
                              title={`View ${src.file} in Evidence Panel`}
                            >
                              <Code className="w-3 h-3 text-[#3B82F6]" />
                              <span className="font-semibold">{src.file.split("/").pop()}</span>
                              {src.start_line && src.end_line && (
                                <span className="text-[#8c909f] text-[10px]">
                                  L{src.start_line}-{src.end_line}
                                </span>
                              )}
                            </button>
                          );
                        })}
                      </div>
                    )}

                    {/* Action & Metadata Footer */}
                    <div className="flex items-center justify-between mt-3 text-[11px] font-mono text-[#8c909f]">
                      <div className="flex items-center gap-3">
                        <span className="flex items-center gap-1">
                          <Cpu className="w-3.5 h-3.5 text-[#3B82F6]" />
                          <span>{item.response.model}</span>
                        </span>
                        <span>•</span>
                        <span className="flex items-center gap-1">
                          <Clock className="w-3.5 h-3.5 text-amber-400" />
                          <span>{Math.round(item.response.latency_ms)} ms</span>
                        </span>
                      </div>

                      <div className="flex items-center gap-1">
                        <button
                          onClick={() => handleCopy(item.response!.answer, idx)}
                          className="flex items-center gap-1 p-1.5 text-[#8c909f] hover:text-[#e2e2e2] hover:bg-[#1C1C1C] rounded transition-colors"
                          title="Copy Markdown Answer"
                        >
                          {copiedIndex === idx ? (
                            <>
                              <Check className="w-3.5 h-3.5 text-[#10B981]" />
                              <span className="text-[#10B981]">Copied</span>
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
                  </div>
                </div>
              ) : item.error ? (
                <div className="self-start max-w-full p-4 rounded-xl bg-[#93000a]/20 border border-[#ffb4ab]/30 text-xs font-mono text-[#ffb4ab]">
                  <p className="font-semibold mb-1">Query Error</p>
                  <p>{item.error}</p>
                </div>
              ) : null}
            </div>
          ))}

          {/* Loading Indicator */}
          {isLoading && (
            <div className="self-start flex items-center gap-3 p-4 rounded-xl bg-[#1C1C1C] border border-[#2A2A2A] text-xs font-mono text-[#adc6ff] animate-pulse">
              <div className="w-2 h-2 rounded-full bg-[#3B82F6] animate-ping"></div>
              <span>Searching codebase & generating grounded answer...</span>
            </div>
          )}
        </div>
      </div>

      {/* Composer Input (Fixed Bottom) */}
      <div className="absolute bottom-0 left-0 right-0 p-4 md:p-6 bg-gradient-to-t from-[#111111] via-[#111111] to-transparent pt-6 z-10">
        <div className="max-w-3xl mx-auto">
          <form onSubmit={handleSubmit} className="relative bg-[#171717] border border-[#2A2A2A] rounded-xl focus-within:border-[#3B82F6] transition-colors flex flex-col shadow-lg">
            <textarea
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              onKeyDown={handleKeyDown}
              disabled={isLoading}
              rows={2}
              placeholder="Ask about this codebase (Cmd + Enter to submit)..."
              className="w-full bg-transparent text-[#e2e2e2] text-sm p-3.5 resize-none focus:outline-none placeholder-[#8c909f] disabled:opacity-50"
            />

            <div className="flex items-center justify-between p-2 border-t border-[#2A2A2A] bg-[#1C1C1C] rounded-b-xl">
              {/* Top-K Control */}
              <div className="flex items-center gap-2 text-xs font-mono text-[#a1a1aa]">
                <button
                  type="button"
                  onClick={() => setShowTopK(!showTopK)}
                  className="flex items-center gap-1 px-2 py-1 rounded hover:bg-[#282a2b] text-[#8c909f] hover:text-[#e2e2e2] transition-colors"
                  title="Configure Top-K retrieval count"
                >
                  <Sliders className="w-3.5 h-3.5 text-[#3B82F6]" />
                  <span>top_k: <strong className="text-[#adc6ff]">{topK}</strong></span>
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
                className="bg-[#3B82F6] hover:bg-[#2563eb] text-[#F5F5F5] w-8 h-8 rounded-lg flex items-center justify-center transition-colors disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer"
                aria-label="Send Query"
              >
                <ArrowUp className="w-4 h-4" />
              </button>
            </div>
          </form>

          <div className="text-center mt-2">
            <span className="text-[11px] text-[#8c909f]">
              DevMind AI answers are strictly grounded in retrieved code context.
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
