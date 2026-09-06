"use client";

import React, { useState } from "react";
import { Terminal, Search, ArrowUp, KeyRound, Route, Network, Globe, Sliders } from "lucide-react";

interface InitialStateProps {
  activeRepository: string | null;
  onSubmit: (query: string, topK: number) => void;
  isLoading: boolean;
}

export function InitialState({
  activeRepository,
  onSubmit,
  isLoading,
}: InitialStateProps) {
  const [inputVal, setInputVal] = useState<string>("");
  const [topK, setTopK] = useState<number>(5);
  const [showTopK, setShowTopK] = useState<boolean>(false);

  const handleSubmit = (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!inputVal.trim() || isLoading) return;
    onSubmit(inputVal.trim(), topK);
  };

  const handleSuggestionClick = (text: string) => {
    setInputVal(text);
    onSubmit(text, topK);
  };

  const repoLabel = activeRepository || "your codebase";

  return (
    <div className="flex-grow flex flex-col items-center justify-center p-4 md:p-8 overflow-y-auto relative animate-fade-in-up font-sans selection:bg-[#3b82f6]/30 selection:text-[#adc6ff]">
      <div className="max-w-2xl w-full flex flex-col items-center text-center gap-6 z-10">
        {/* Terminal Icon & Typography */}
        <div className="space-y-3 flex flex-col items-center">
          <div className="w-12 h-12 bg-[#12151b] border border-[#222733] rounded-xl flex items-center justify-center mb-1 shadow-sm">
            <Terminal className="w-6 h-6 text-[#adc6ff]" />
          </div>
          <h2 className="text-2xl md:text-3xl font-semibold text-[#f3f4f6] tracking-tight leading-tight">
            Understand your codebase.
          </h2>
          <p className="text-sm text-[#9ca3af] max-w-lg leading-relaxed">
            Ask questions about your repository, trace execution flows, find implementations, and inspect the code behind every answer.
          </p>
        </div>

        {/* Search Input Area */}
        <form onSubmit={handleSubmit} className="w-full max-w-xl relative group mt-2">
          <div className="relative rounded-xl border border-[#222733] bg-[#0c0e12] focus-within:border-[#3b82f6] focus-within:ring-1 focus-within:ring-[#3b82f6]/30 transition-all shadow-lg overflow-hidden">
            <div className="flex items-center px-3.5 py-1">
              <Search className="w-4 h-4 text-[#6b7280] shrink-0 mr-2.5" />
              <input
                type="text"
                value={inputVal}
                onChange={(e) => setInputVal(e.target.value)}
                placeholder={`Ask anything about ${repoLabel}...`}
                disabled={isLoading}
                className="w-full h-12 bg-transparent text-[#f3f4f6] text-sm placeholder-[#6b7280] focus:outline-none disabled:opacity-50 font-sans"
              />

              <div className="flex items-center gap-2 shrink-0">
                {/* Top-K Configuration Toggle */}
                <button
                  type="button"
                  onClick={() => setShowTopK(!showTopK)}
                  className="flex items-center gap-1 px-2 py-1 rounded bg-[#14171d] border border-[#222733] hover:bg-[#1a1e27] text-[11px] font-mono text-[#9ca3af] transition-colors"
                  title="Configure Top-K retrieval count"
                >
                  <Sliders className="w-3 h-3 text-[#3b82f6]" />
                  <span>k:{topK}</span>
                </button>

                <button
                  type="submit"
                  disabled={!inputVal.trim() || isLoading}
                  className="w-8 h-8 flex items-center justify-center bg-[#3b82f6] text-white rounded-lg hover:bg-[#2563eb] transition-colors disabled:opacity-30 disabled:cursor-not-allowed cursor-pointer shadow-sm active:scale-[0.98]"
                  aria-label="Submit Query"
                >
                  <ArrowUp className="w-4 h-4" />
                </button>
              </div>
            </div>

            {/* Expandable Top-K Slider */}
            {showTopK && (
              <div className="px-4 py-2.5 border-t border-[#1e232d] bg-[#111317] flex items-center justify-between text-xs font-mono text-[#9ca3af] animate-fade-in-up">
                <span className="text-[11px]">Context Chunks (top_k):</span>
                <div className="flex items-center gap-3">
                  <input
                    type="range"
                    min={1}
                    max={20}
                    value={topK}
                    onChange={(e) => setTopK(Number(e.target.value))}
                    className="w-28 accent-[#3b82f6] cursor-pointer"
                  />
                  <span className="text-[#adc6ff] font-bold w-4 text-right">{topK}</span>
                </div>
              </div>
            )}
          </div>
        </form>

        {/* Suggestion Chips Grid */}
        <div className="w-full max-w-xl grid grid-cols-1 sm:grid-cols-2 gap-2.5 mt-2">
          <button
            type="button"
            onClick={() => handleSuggestionClick("Where is authentication implemented?")}
            className="flex items-start gap-2.5 p-3 bg-[#111419] border border-[#1e232d] hover:border-[#3b82f6]/40 hover:bg-[#151921] transition-all text-left rounded-xl group cursor-pointer"
          >
            <KeyRound className="w-4 h-4 text-[#6b7280] mt-0.5 group-hover:text-[#adc6ff] shrink-0" />
            <div>
              <p className="font-medium text-xs text-[#f3f4f6] leading-snug">Where is authentication implemented?</p>
              <p className="text-[10px] text-[#6b7280] mt-0.5">Symbol lookup & security verification</p>
            </div>
          </button>

          <button
            type="button"
            onClick={() => handleSuggestionClick("Trace the login execution flow")}
            className="flex items-start gap-2.5 p-3 bg-[#111419] border border-[#1e232d] hover:border-[#3b82f6]/40 hover:bg-[#151921] transition-all text-left rounded-xl group cursor-pointer"
          >
            <Route className="w-4 h-4 text-[#6b7280] mt-0.5 group-hover:text-[#adc6ff] shrink-0" />
            <div>
              <p className="font-medium text-xs text-[#f3f4f6] leading-snug">Trace the login execution flow</p>
              <p className="text-[10px] text-[#6b7280] mt-0.5">Multi-hop call graph dependency tracing</p>
            </div>
          </button>

          <button
            type="button"
            onClick={() => handleSuggestionClick("Explain the repository architecture")}
            className="flex items-start gap-2.5 p-3 bg-[#111419] border border-[#1e232d] hover:border-[#3b82f6]/40 hover:bg-[#151921] transition-all text-left rounded-xl group cursor-pointer"
          >
            <Network className="w-4 h-4 text-[#6b7280] mt-0.5 group-hover:text-[#adc6ff] shrink-0" />
            <div>
              <p className="font-medium text-xs text-[#f3f4f6] leading-snug">Explain the repository architecture</p>
              <p className="text-[10px] text-[#6b7280] mt-0.5">High-level codebase structural summary</p>
            </div>
          </button>

          <button
            type="button"
            onClick={() => handleSuggestionClick("Find all API route handlers")}
            className="flex items-start gap-2.5 p-3 bg-[#111419] border border-[#1e232d] hover:border-[#3b82f6]/40 hover:bg-[#151921] transition-all text-left rounded-xl group cursor-pointer"
          >
            <Globe className="w-4 h-4 text-[#6b7280] mt-0.5 group-hover:text-[#adc6ff] shrink-0" />
            <div>
              <p className="font-medium text-xs text-[#f3f4f6] leading-snug">Find all API route handlers</p>
              <p className="text-[10px] text-[#6b7280] mt-0.5">HTTP endpoints and request handlers</p>
            </div>
          </button>
        </div>
      </div>
    </div>
  );
}
