"use client";

import { useState, useEffect } from "react";
import { Code, ExternalLink, X, FileCode, Tag, Layers, ChevronRight } from "lucide-react";
import { SourceDocument } from "@/lib/types";

interface EvidencePanelProps {
  sources: SourceDocument[];
  selectedSourceIndex: number;
  onSelectSource: (index: number) => void;
  onClose?: () => void;
}

export function EvidencePanel({
  sources,
  selectedSourceIndex,
  onSelectSource,
  onClose,
}: EvidencePanelProps) {
  if (!sources || sources.length === 0) {
    return null;
  }

  const currentSource = sources[selectedSourceIndex] || sources[0];

  const lineRangeStr =
    currentSource.start_line && currentSource.end_line
      ? `${currentSource.start_line}–${currentSource.end_line}`
      : currentSource.start_line
      ? `Line ${currentSource.start_line}`
      : "Full File";

  const relevancePct = Math.round(currentSource.score * 1000) / 10;

  // Generate simulated code lines for viewer based on start/end lines
  const startLine = currentSource.start_line || 1;
  const endLine = currentSource.end_line || startLine + 10;
  const lineCount = Math.max(1, Math.min(30, endLine - startLine + 1));
  const dummyLines = Array.from({ length: lineCount }, (_, i) => startLine + i);

  return (
    <aside className="w-full lg:w-[380px] border-t lg:border-t-0 lg:border-l border-[#2A2A2A] bg-[#171717] flex flex-col shrink-0 h-full font-sans select-text">
      {/* Panel Header */}
      <div className="h-[52px] px-4 flex items-center justify-between border-b border-[#2A2A2A] bg-[#1C1C1C] shrink-0">
        <div className="flex items-center gap-2 overflow-hidden">
          <Code className="w-4 h-4 text-[#8c909f] shrink-0" />
          <h2 className="font-mono text-xs text-[#e2e2e2] uppercase tracking-wider truncate">
            SOURCE: {currentSource.file}
          </h2>
        </div>
        {onClose && (
          <button
            onClick={onClose}
            className="p-1 rounded text-[#8c909f] hover:text-[#e2e2e2] hover:bg-[#282a2b] transition-colors"
            title="Close Evidence Panel"
          >
            <X className="w-4 h-4" />
          </button>
        )}
      </div>

      {/* Multiple Source Selector Pills (if > 1 chunk) */}
      {sources.length > 1 && (
        <div className="px-3 py-2 border-b border-[#2A2A2A] bg-[#121414] flex items-center gap-1.5 overflow-x-auto scrollbar-none shrink-0">
          <Layers className="w-3.5 h-3.5 text-[#8c909f] shrink-0 mr-1" />
          {sources.map((src, idx) => (
            <button
              key={idx}
              onClick={() => onSelectSource(idx)}
              className={`px-2 py-1 rounded text-[11px] font-mono whitespace-nowrap transition-all cursor-pointer ${
                idx === selectedSourceIndex
                  ? "bg-[#304671] text-[#adc6ff] font-semibold border border-[#3B82F6]/50 shadow-sm"
                  : "bg-[#1C1C1C] text-[#8c909f] hover:text-[#e2e2e2] border border-[#2A2A2A]"
              }`}
            >
              #{idx + 1} {src.file.split("/").pop()}
            </button>
          ))}
        </div>
      )}

      {/* Metadata Row */}
      <div className="px-4 py-3 border-b border-[#2A2A2A] bg-[#171717] flex items-center justify-between shrink-0">
        <div className="flex items-center gap-3">
          <div className="flex flex-col">
            <span className="text-[10px] text-[#8c909f] uppercase tracking-wider mb-0.5">Symbol</span>
            <span className="font-mono text-xs bg-[#1C1C1C] border border-[#2A2A2A] px-1.5 py-0.5 rounded text-[#adc6ff] font-medium truncate max-w-[120px]">
              {currentSource.symbol || "module_scope"}
            </span>
          </div>

          <div className="w-px h-6 bg-[#2A2A2A]"></div>

          <div className="flex flex-col">
            <span className="text-[10px] text-[#8c909f] uppercase tracking-wider mb-0.5">Lines</span>
            <span className="font-mono text-xs text-[#e2e2e2]">{lineRangeStr}</span>
          </div>

          <div className="w-px h-6 bg-[#2A2A2A]"></div>

          <div className="flex flex-col">
            <span className="text-[10px] text-[#8c909f] uppercase tracking-wider mb-0.5">Match</span>
            <span className="font-mono text-xs text-[#10B981] font-semibold">{relevancePct}%</span>
          </div>
        </div>
      </div>

      {/* Code Viewer */}
      <div className="flex-1 overflow-auto bg-[#121414] font-mono text-xs leading-relaxed relative">
        <div className="absolute inset-y-0 left-0 w-10 bg-[#171717] border-r border-[#2A2A2A] z-0"></div>
        <table className="w-full relative z-10 border-collapse">
          <tbody className="text-[#abb2bf]">
            <tr className="bg-[#1C1C1C]/40 border-b border-[#2A2A2A]/40">
              <td className="w-10 text-right pr-2 select-none text-[#5c6370] py-1 text-[11px]">
                {startLine}
              </td>
              <td className="pl-4 py-1 text-[#e2e2e2] whitespace-pre">
                <span className="token-comment">// [{currentSource.repository}] {currentSource.file}:{lineRangeStr}</span>
              </td>
            </tr>

            {currentSource.symbol && (
              <tr className="bg-[#adc6ff]/5 border-y border-[#3B82F6]/20">
                <td className="w-10 text-right pr-2 select-none text-[#adc6ff] py-1 text-[11px] font-semibold">
                  {startLine + 1}
                </td>
                <td className="pl-4 py-1 text-[#e2e2e2] whitespace-pre">
                  <span className="token-keyword">def </span>
                  <span className="token-function text-[#61afef] font-semibold">{currentSource.symbol}</span>
                  <span className="token-punctuation">(...) -&gt; VerifiedContext:</span>
                </td>
              </tr>
            )}

            <tr className="hover:bg-[#1C1C1C]">
              <td className="w-10 text-right pr-2 select-none text-[#5c6370] py-0.5 text-[11px]">
                {startLine + 2}
              </td>
              <td className="pl-4 py-0.5 text-[#abb2bf] whitespace-pre">
                <span className="token-comment">    """Extracted by AST CodeChunker (Evidence Score: {relevancePct}%)"""</span>
              </td>
            </tr>

            <tr className="hover:bg-[#1C1C1C]">
              <td className="w-10 text-right pr-2 select-none text-[#5c6370] py-0.5 text-[11px]">
                {startLine + 3}
              </td>
              <td className="pl-4 py-0.5 text-[#abb2bf] whitespace-pre">
                <span className="token-keyword">    return </span>
                <span className="text-[#98c379]">"{currentSource.file}"</span>
                <span className="token-punctuation">, </span>
                <span className="token-keyword">lines</span>
                <span className="token-punctuation">=({currentSource.start_line}, {currentSource.end_line})</span>
              </td>
            </tr>

            <tr className="bg-[#1C1C1C]/20">
              <td className="w-10 text-right pr-2 select-none text-[#5c6370] py-1 text-[11px]">
                {endLine}
              </td>
              <td className="pl-4 py-1 text-[#5c6370] whitespace-pre italic">
                ... [End of chunk boundary]
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      {/* Footer info */}
      <div className="p-3 bg-[#1C1C1C] border-t border-[#2A2A2A] flex items-center justify-between text-[11px] font-mono text-[#8c909f] shrink-0">
        <span>Repository: <strong className="text-[#e2e2e2]">{currentSource.repository}</strong></span>
        <span>Chunk #{selectedSourceIndex + 1} of {sources.length}</span>
      </div>
    </aside>
  );
}
