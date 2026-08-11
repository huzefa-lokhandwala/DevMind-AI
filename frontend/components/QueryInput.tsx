"use client";

import { useState } from "react";
import { Search, Loader2, Sliders, History, CornerDownLeft } from "lucide-react";

interface QueryInputProps {
  onSubmit: (query: string, topK: number) => void;
  isLoading: boolean;
  history: string[];
  onSelectHistory: (query: string) => void;
}

export function QueryInput({
  onSubmit,
  isLoading,
  history,
  onSelectHistory,
}: QueryInputProps) {
  const [query, setQuery] = useState<string>("");
  const [topK, setTopK] = useState<number>(5);
  const [showTopKSlider, setShowTopKSlider] = useState<boolean>(false);

  const handleSubmit = (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!query.trim() || isLoading) return;
    onSubmit(query.trim(), topK);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if ((e.metaKey || e.ctrlKey) && e.key === "Enter") {
      e.preventDefault();
      handleSubmit();
    }
  };

  return (
    <div className="w-full space-y-3 font-sans">
      <form onSubmit={handleSubmit} className="relative group">
        <div className="relative rounded-xl border border-zinc-800 bg-zinc-900/90 shadow-lg group-focus-within:border-indigo-500/60 group-focus-within:ring-1 group-focus-within:ring-indigo-500/40 transition-all overflow-hidden">
          {/* Main Textarea */}
          <textarea
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask anything about the codebase (e.g. 'Where is VerificationEngine implemented and trace its score calculation?')..."
            rows={3}
            disabled={isLoading}
            className="w-full p-4 bg-transparent text-zinc-100 placeholder:text-zinc-500 text-sm font-sans resize-none focus:outline-none disabled:opacity-50"
          />

          {/* Controls Footer */}
          <div className="flex items-center justify-between px-4 py-2.5 border-t border-zinc-800/60 bg-zinc-950/40">
            {/* Top-K Toggle & Controls */}
            <div className="flex items-center space-x-3 text-xs font-mono text-zinc-400">
              <button
                type="button"
                onClick={() => setShowTopKSlider(!showTopKSlider)}
                className="flex items-center space-x-1.5 px-2 py-1 rounded hover:bg-zinc-800 text-zinc-300 transition-colors"
              >
                <Sliders className="w-3.5 h-3.5 text-indigo-400" />
                <span>top_k:</span>
                <span className="font-bold text-indigo-300">{topK}</span>
              </button>

              {showTopKSlider && (
                <div className="flex items-center space-x-2 animate-in fade-in duration-150 bg-zinc-900 px-3 py-1 rounded border border-zinc-800">
                  <input
                    type="range"
                    min={1}
                    max={20}
                    value={topK}
                    onChange={(e) => setTopK(Number(e.target.value))}
                    className="w-24 accent-indigo-500 cursor-pointer"
                  />
                  <span className="text-[11px] text-zinc-400 font-mono w-4">{topK}</span>
                </div>
              )}
            </div>

            {/* Keyboard shortcut hint & Submit button */}
            <div className="flex items-center space-x-3">
              <span className="hidden sm:flex items-center space-x-1 text-[11px] font-mono text-zinc-500">
                <kbd className="px-1.5 py-0.5 rounded bg-zinc-800 border border-zinc-700 text-zinc-400">⌘</kbd>
                <span>+</span>
                <kbd className="px-1.5 py-0.5 rounded bg-zinc-800 border border-zinc-700 text-zinc-400">Enter</kbd>
              </span>

              <button
                type="submit"
                disabled={!query.trim() || isLoading}
                className="flex items-center space-x-1.5 px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white font-mono text-xs font-semibold shadow-md transition-all disabled:opacity-40 disabled:cursor-not-allowed"
              >
                {isLoading ? (
                  <>
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    <span>Searching...</span>
                  </>
                ) : (
                  <>
                    <Search className="w-3.5 h-3.5" />
                    <span>Query</span>
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      </form>

      {/* Query History Pills */}
      {history.length > 0 && (
        <div className="flex items-center space-x-2 text-xs font-mono overflow-x-auto pb-1 scrollbar-none">
          <History className="w-3.5 h-3.5 text-zinc-500 shrink-0" />
          <span className="text-zinc-500 text-[11px] shrink-0">Recent:</span>
          {history.slice(-5).reverse().map((item, idx) => (
            <button
              key={idx}
              onClick={() => {
                setQuery(item);
                onSelectHistory(item);
              }}
              className="px-2.5 py-1 rounded-full bg-zinc-900 border border-zinc-800 text-zinc-400 hover:text-indigo-300 hover:border-indigo-500/40 transition-colors shrink-0 max-w-[200px] truncate"
              title={item}
            >
              {item}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
