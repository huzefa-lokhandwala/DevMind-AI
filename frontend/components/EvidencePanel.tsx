"use client";

import React, { useState } from "react";
import {
  Code,
  X,
  FileCode,
  Layers,
  Copy,
  Check,
  ExternalLink,
  ShieldCheck,
  FileText,
} from "lucide-react";
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
  const [copiedSnippet, setCopiedSnippet] = useState<boolean>(false);
  const [copiedPath, setCopiedPath] = useState<boolean>(false);

  if (!sources || sources.length === 0) {
    return null;
  }

  const currentSource = sources[selectedSourceIndex] || sources[0];

  const lineRangeStr =
    currentSource.start_line && currentSource.end_line
      ? `Lines ${currentSource.start_line}–${currentSource.end_line}`
      : currentSource.start_line
      ? `Line ${currentSource.start_line}`
      : "Full Chunk";

  const relevancePct = Math.round(currentSource.score * 1000) / 10;
  const fileName = currentSource.file.split("/").pop() || currentSource.file;
  const fullPath = currentSource.file_path || currentSource.file;

  const handleCopySnippet = () => {
    if (!currentSource.snippet) return;
    navigator.clipboard.writeText(currentSource.snippet);
    setCopiedSnippet(true);
    setTimeout(() => setCopiedSnippet(false), 2000);
  };

  const handleCopyPath = () => {
    navigator.clipboard.writeText(fullPath);
    setCopiedPath(true);
    setTimeout(() => setCopiedPath(false), 2000);
  };

  // Prepare line numbered snippet lines if snippet exists
  const snippetLines = currentSource.snippet
    ? currentSource.snippet.split("\n")
    : [];
  const baseLineNumber = currentSource.start_line || 1;

  return (
    <aside className="w-full lg:w-[420px] xl:w-[460px] border-t lg:border-t-0 lg:border-l border-[#2A2A2A] bg-[#141414] flex flex-col shrink-0 h-full font-sans select-text shadow-xl z-20">
      {/* Panel Header */}
      <div className="h-[52px] px-4 flex items-center justify-between border-b border-[#2A2A2A] bg-[#181818] shrink-0">
        <div className="flex items-center gap-2 overflow-hidden">
          <ShieldCheck className="w-4 h-4 text-[#3B82F6] shrink-0" />
          <h2 className="font-mono text-xs font-bold text-[#f5f5f5] uppercase tracking-wider truncate">
            Evidence Inspector
          </h2>
          <span className="bg-[#1f293d] text-[#adc6ff] text-[10px] font-mono px-1.5 py-0.5 rounded border border-[#2e3b52] shrink-0">
            #{selectedSourceIndex + 1} of {sources.length}
          </span>
        </div>
        {onClose && (
          <button
            type="button"
            onClick={onClose}
            className="p-1 rounded text-[#8c909f] hover:text-[#e2e2e2] hover:bg-[#252525] transition-colors cursor-pointer"
            title="Close Evidence Inspector"
          >
            <X className="w-4 h-4" />
          </button>
        )}
      </div>

      {/* Multiple Source Selector Tabs (if > 1 source) */}
      {sources.length > 1 && (
        <div className="px-3 py-2 border-b border-[#2A2A2A] bg-[#111111] flex items-center gap-1.5 overflow-x-auto scrollbar-none shrink-0">
          <Layers className="w-3.5 h-3.5 text-[#8c909f] shrink-0 mr-0.5" />
          {sources.map((src, idx) => {
            const isSelected = idx === selectedSourceIndex;
            const tabFileName = src.file.split("/").pop() || src.file;
            return (
              <button
                key={idx}
                type="button"
                onClick={() => onSelectSource(idx)}
                className={`px-2.5 py-1 rounded text-[11px] font-mono whitespace-nowrap transition-all cursor-pointer flex items-center gap-1.5 ${
                  isSelected
                    ? "bg-[#304671] text-[#adc6ff] font-semibold border border-[#3B82F6]/60 shadow-sm"
                    : "bg-[#1C1C1C] text-[#8c909f] hover:text-[#e2e2e2] border border-[#2A2A2A]"
                }`}
              >
                <span>[{idx + 1}]</span>
                <span className="truncate max-w-[110px]">{tabFileName}</span>
              </button>
            );
          })}
        </div>
      )}

      {/* Metadata Detail Section */}
      <div className="p-4 border-b border-[#2A2A2A] bg-[#171717] flex flex-col gap-2.5 shrink-0">
        {/* File and Copy Path */}
        <div className="flex items-start justify-between gap-2">
          <div className="min-w-0">
            <div className="flex items-center gap-1.5 text-xs font-mono font-bold text-[#f5f5f5]">
              <FileCode className="w-4 h-4 text-[#3B82F6] shrink-0" />
              <span className="truncate">{fileName}</span>
            </div>
            <p className="text-[11px] font-mono text-[#8c909f] truncate mt-0.5" title={fullPath}>
              {fullPath}
            </p>
          </div>

          <button
            type="button"
            onClick={handleCopyPath}
            className="shrink-0 p-1.5 rounded text-[#8c909f] hover:text-[#e2e2e2] hover:bg-[#252525] transition-colors font-mono text-[10px] flex items-center gap-1 cursor-pointer"
            title="Copy full file path"
          >
            {copiedPath ? (
              <>
                <Check className="w-3 h-3 text-[#10B981]" />
                <span className="text-[#10B981]">Copied</span>
              </>
            ) : (
              <>
                <Copy className="w-3 h-3" />
                <span>Path</span>
              </>
            )}
          </button>
        </div>

        {/* Badges Row */}
        <div className="flex flex-wrap items-center gap-2 pt-1">
          <span className="font-mono text-[11px] bg-[#1C1C1C] border border-[#2A2A2A] px-2 py-0.5 rounded text-[#e2e2e2]">
            {lineRangeStr}
          </span>

          {currentSource.symbol && (
            <span className="font-mono text-[11px] bg-[#1f293d] border border-[#2e3b52] px-2 py-0.5 rounded text-[#adc6ff] truncate max-w-[180px]">
              {currentSource.symbol}
            </span>
          )}

          <span
            className={`font-mono text-[11px] px-2 py-0.5 rounded font-semibold ${
              relevancePct >= 80
                ? "bg-[#064e3b]/40 text-[#34d399] border border-[#059669]/40"
                : relevancePct >= 60
                ? "bg-[#1e3a8a]/40 text-[#93c5fd] border border-[#2563eb]/40"
                : "bg-[#27272a] text-[#a1a1aa] border border-[#3f3f46]"
            }`}
          >
            {relevancePct}% relevance
          </span>
        </div>
      </div>

      {/* Code Viewer Area */}
      <div className="flex-1 flex flex-col min-h-0 bg-[#0d1117]">
        {/* Code Header Bar */}
        <div className="flex items-center justify-between px-4 py-2 bg-[#161b22] border-b border-[#2A2A2A] text-[11px] font-mono text-[#8c909f]">
          <span className="flex items-center gap-1.5 text-[#adc6ff] font-semibold">
            <Code className="w-3.5 h-3.5 text-[#3B82F6]" />
            <span>Extracted AST Chunk Content</span>
          </span>

          {currentSource.snippet && (
            <button
              type="button"
              onClick={handleCopySnippet}
              className="flex items-center gap-1 text-[#8c909f] hover:text-[#e2e2e2] transition-colors cursor-pointer"
              title="Copy chunk snippet"
            >
              {copiedSnippet ? (
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
          )}
        </div>

        {/* Line-Numbered Source Viewer */}
        <div className="flex-1 overflow-auto font-mono text-xs leading-relaxed p-0 relative">
          {snippetLines.length > 0 ? (
            <table className="w-full border-collapse">
              <tbody className="text-[#e6edf3]">
                {snippetLines.map((line, lIdx) => {
                  const lineNumber = baseLineNumber + lIdx;
                  return (
                    <tr
                      key={lIdx}
                      className="hover:bg-[#161b22] transition-colors group"
                    >
                      <td className="w-12 text-right pr-3 select-none text-[#484f58] py-0.5 text-[11px] border-r border-[#21262d] bg-[#0d1117] sticky left-0 group-hover:text-[#8b949e]">
                        {lineNumber}
                      </td>
                      <td className="pl-4 pr-3 py-0.5 whitespace-pre font-mono text-[12px] text-[#c9d1d9] overflow-x-visible">
                        {line}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          ) : (
            <div className="p-6 text-center text-xs font-mono text-[#8c909f] flex flex-col items-center gap-2">
              <FileText className="w-6 h-6 text-[#2A2A2A]" />
              <span>Target File: {fullPath}</span>
              <span className="text-[11px] text-[#555]">{lineRangeStr}</span>
            </div>
          )}
        </div>
      </div>

      {/* Footer Info */}
      <div className="p-3 bg-[#181818] border-t border-[#2A2A2A] flex items-center justify-between text-[11px] font-mono text-[#8c909f] shrink-0">
        <span className="truncate max-w-[220px]">
          Repo: <strong className="text-[#e2e2e2]">{currentSource.repository}</strong>
        </span>
        <span className="text-[#adc6ff]">Verified Evidence</span>
      </div>
    </aside>
  );
}
