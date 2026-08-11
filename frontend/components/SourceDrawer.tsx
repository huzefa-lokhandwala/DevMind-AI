"use client";

import { useState } from "react";
import { FileCode, ChevronDown, ChevronRight, Layers, Tag } from "lucide-react";
import { SourceDocument } from "@/lib/types";

interface SourceDrawerProps {
  sources: SourceDocument[];
}

export function SourceDrawer({ sources }: SourceDrawerProps) {
  const [isOpen, setIsOpen] = useState<boolean>(true);

  if (!sources || sources.length === 0) return null;

  return (
    <div className="w-full border border-zinc-800 bg-zinc-900/60 rounded-xl shadow-lg overflow-hidden font-sans">
      {/* Drawer Header Toggle */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="w-full flex items-center justify-between px-6 py-3 bg-zinc-950/60 hover:bg-zinc-950 transition-colors border-b border-zinc-800/80 text-left"
      >
        <div className="flex items-center space-x-2.5">
          <Layers className="w-4 h-4 text-indigo-400" />
          <h4 className="text-xs font-semibold text-zinc-200 font-mono">
            Retrieved Context Sources ({sources.length} Chunks)
          </h4>
        </div>
        <div className="flex items-center space-x-2 text-zinc-400">
          <span className="text-[11px] font-mono text-zinc-500">
            {isOpen ? "Collapse" : "Expand"}
          </span>
          {isOpen ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
        </div>
      </button>

      {/* Drawer Content Body */}
      {isOpen && (
        <div className="p-4 space-y-2.5">
          {sources.map((source, index) => {
            const scorePercent = Math.round(source.score * 1000) / 10;
            const lineRange =
              source.start_line && source.end_line
                ? `L${source.start_line}-${source.end_line}`
                : source.start_line
                ? `L${source.start_line}`
                : null;

            return (
              <div
                key={index}
                className="p-3 rounded-lg border border-zinc-800 bg-zinc-950/80 hover:border-zinc-700 transition-colors flex items-center justify-between font-mono text-xs"
              >
                <div className="flex items-center space-x-3 overflow-hidden">
                  <div className="p-1.5 rounded bg-indigo-950/60 text-indigo-400 border border-indigo-500/20 shrink-0">
                    <FileCode className="w-3.5 h-3.5" />
                  </div>
                  <div className="space-y-0.5 truncate">
                    <div className="flex items-center space-x-2">
                      <span className="font-semibold text-zinc-100 truncate">{source.file}</span>
                      {source.symbol && (
                        <span className="px-1.5 py-0.2 rounded bg-indigo-500/10 text-indigo-300 border border-indigo-500/20 text-[10px] flex items-center space-x-1 shrink-0">
                          <Tag className="w-2.5 h-2.5" />
                          <span>{source.symbol}</span>
                        </span>
                      )}
                    </div>
                    <div className="text-[11px] text-zinc-500 flex items-center space-x-2">
                      <span>repo: {source.repository}</span>
                      {lineRange && (
                        <>
                          <span>•</span>
                          <span className="text-zinc-400">{lineRange}</span>
                        </>
                      )}
                    </div>
                  </div>
                </div>

                {/* Relevance Score Badge */}
                <div className="shrink-0 text-right ml-3">
                  <div className="px-2 py-0.5 rounded bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 font-bold text-xs">
                    {scorePercent}%
                  </div>
                  <div className="text-[10px] text-zinc-500 mt-0.5">relevance</div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
