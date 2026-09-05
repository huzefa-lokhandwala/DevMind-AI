"use client";

import React, { useState } from "react";
import {
  Layers,
  ChevronDown,
  ChevronUp,
  ExternalLink,
} from "lucide-react";
import { SourceDocument } from "@/lib/types";

interface SourceCardListProps {
  sources: SourceDocument[];
  selectedSourceIndex: number;
  onSelectSource: (index: number) => void;
}

export function SourceCardList({
  sources,
  selectedSourceIndex,
  onSelectSource,
}: SourceCardListProps) {
  const [expandedIndices, setExpandedIndices] = useState<Set<number>>(new Set());

  if (!sources || sources.length === 0) {
    return null;
  }

  const toggleExpand = (e: React.MouseEvent, idx: number) => {
    e.stopPropagation();
    setExpandedIndices((prev) => {
      const next = new Set(prev);
      if (next.has(idx)) {
        next.delete(idx);
      } else {
        next.add(idx);
      }
      return next;
    });
  };

  return (
    <div className="mt-5 pt-4 border-t border-[#2A2A2A]/80">
      {/* Evidence Section Header */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <Layers className="w-4 h-4 text-[#3B82F6]" />
          <h3 className="text-xs font-mono font-semibold text-[#adc6ff] uppercase tracking-wider">
            Retrieved Code Evidence ({sources.length})
          </h3>
        </div>
        <span className="text-[11px] font-mono text-[#8c909f]">
          Click card to inspect source chunk
        </span>
      </div>

      {/* Source Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-2.5">
        {sources.map((src, idx) => {
          const isSelected = idx === selectedSourceIndex;
          const isExpanded = expandedIndices.has(idx);
          const fileName = src.file.split("/").pop() || src.file;
          const fullPath = src.file_path || src.file;
          const lineStr =
            src.start_line && src.end_line
              ? `L${src.start_line}–${src.end_line}`
              : src.start_line
              ? `Line ${src.start_line}`
              : "Full Chunk";
          const matchScore = Math.round(src.score * 100);

          return (
            <div
              key={idx}
              onClick={() => onSelectSource(idx)}
              className={`group flex flex-col rounded-xl border transition-all cursor-pointer p-3 text-left ${
                isSelected
                  ? "bg-[#182338] border-[#3B82F6] shadow-sm ring-1 ring-[#3B82F6]/50"
                  : "bg-[#161616] border-[#2A2A2A] hover:border-[#424754] hover:bg-[#1C1C1C]"
              }`}
            >
              {/* Top Row: Rank, Filename, Score */}
              <div className="flex items-start justify-between gap-2">
                <div className="flex items-center gap-2 min-w-0">
                  <span
                    className={`shrink-0 w-5 h-5 rounded flex items-center justify-center font-mono text-[11px] font-bold ${
                      isSelected
                        ? "bg-[#3B82F6] text-white"
                        : "bg-[#252525] text-[#a1a1aa] group-hover:text-white"
                    }`}
                  >
                    {idx + 1}
                  </span>
                  <div className="truncate">
                    <span className="font-mono text-xs font-semibold text-[#f5f5f5] group-hover:text-[#adc6ff] transition-colors truncate block">
                      {fileName}
                    </span>
                  </div>
                </div>

                <div className="flex items-center gap-1.5 shrink-0">
                  <span
                    className={`font-mono text-[10px] px-1.5 py-0.5 rounded font-semibold ${
                      matchScore >= 80
                        ? "bg-[#064e3b]/50 text-[#34d399] border border-[#059669]/40"
                        : matchScore >= 60
                        ? "bg-[#1e3a8a]/50 text-[#93c5fd] border border-[#2563eb]/40"
                        : "bg-[#27272a] text-[#a1a1aa] border border-[#3f3f46]"
                    }`}
                  >
                    {matchScore}% match
                  </span>
                </div>
              </div>

              {/* Path & Line Range */}
              <div className="mt-1.5 flex items-center justify-between text-[11px] font-mono text-[#8c909f] gap-2">
                <span className="truncate text-[#a1a1aa]" title={fullPath}>
                  {fullPath}
                </span>
                <span className="shrink-0 bg-[#222222] px-1.5 py-0.5 rounded text-[#cbd5e1]">
                  {lineStr}
                </span>
              </div>

              {/* Symbol row (if present) */}
              {src.symbol && (
                <div className="mt-2 flex items-center gap-1.5 text-[11px] font-mono">
                  <span className="text-[#8c909f]">symbol:</span>
                  <span className="text-[#adc6ff] bg-[#1f293d] px-1.5 py-0.5 rounded border border-[#2e3b52] truncate">
                    {src.symbol}
                  </span>
                </div>
              )}

              {/* Quick Snippet Accordion */}
              {src.snippet && (
                <div className="mt-2 pt-2 border-t border-[#2A2A2A]/50">
                  <div className="flex items-center justify-between">
                    <button
                      type="button"
                      onClick={(e) => toggleExpand(e, idx)}
                      className="inline-flex items-center gap-1 text-[10px] font-mono text-[#8c909f] hover:text-[#adc6ff] transition-colors cursor-pointer"
                    >
                      {isExpanded ? (
                        <>
                          <ChevronUp className="w-3 h-3" />
                          <span>Hide snippet</span>
                        </>
                      ) : (
                        <>
                          <ChevronDown className="w-3 h-3" />
                          <span>Preview snippet</span>
                        </>
                      )}
                    </button>

                    <span className="text-[10px] font-mono text-[#8c909f] group-hover:text-[#adc6ff] transition-colors inline-flex items-center gap-0.5">
                      <span>Inspect</span>
                      <ExternalLink className="w-2.5 h-2.5" />
                    </span>
                  </div>

                  {isExpanded && (
                    <pre className="mt-2 p-2 bg-[#0d1117] rounded border border-[#2A2A2A] font-mono text-[11px] text-[#e6edf3] overflow-x-auto max-h-36 leading-relaxed whitespace-pre-wrap">
                      <code>{src.snippet}</code>
                    </pre>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
