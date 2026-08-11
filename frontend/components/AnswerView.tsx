"use client";

import { useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Cpu, Clock, Check, Copy, Sparkles } from "lucide-react";
import { QueryResponse } from "@/lib/types";

interface AnswerViewProps {
  response: QueryResponse;
}

export function AnswerView({ response }: AnswerViewProps) {
  const [copied, setCopied] = useState<boolean>(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(response.answer);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="w-full bg-zinc-900/80 border border-zinc-800 rounded-xl shadow-xl overflow-hidden font-sans">
      {/* Answer View Header */}
      <div className="flex items-center justify-between px-6 py-3.5 border-b border-zinc-800 bg-zinc-950/60">
        <div className="flex items-center space-x-2">
          <Sparkles className="w-4 h-4 text-indigo-400" />
          <h3 className="text-sm font-semibold text-zinc-100 font-mono">DevMind Architecture Answer</h3>
        </div>

        <div className="flex items-center space-x-3">
          {/* Copy Button */}
          <button
            onClick={handleCopy}
            className="flex items-center space-x-1.5 px-2.5 py-1 rounded border border-zinc-800 bg-zinc-900 hover:bg-zinc-800 text-xs font-mono text-zinc-300 transition-colors"
          >
            {copied ? (
              <>
                <Check className="w-3.5 h-3.5 text-emerald-400" />
                <span className="text-emerald-400">Copied</span>
              </>
            ) : (
              <>
                <Copy className="w-3.5 h-3.5 text-zinc-400" />
                <span>Copy Answer</span>
              </>
            )}
          </button>
        </div>
      </div>

      {/* Markdown Content Area */}
      <div className="p-6 text-zinc-200 text-sm leading-relaxed overflow-x-auto">
        <article className="prose prose-invert prose-zinc max-w-none prose-p:leading-relaxed prose-pre:bg-zinc-950 prose-pre:border prose-pre:border-zinc-800 prose-code:font-mono prose-code:text-indigo-300 prose-headings:font-mono prose-headings:text-zinc-100 font-sans">
          <ReactMarkdown remarkPlugins={[remarkGfm]}>
            {response.answer}
          </ReactMarkdown>
        </article>
      </div>

      {/* Model & Latency Footer Metadata */}
      <div className="flex items-center justify-between px-6 py-2.5 border-t border-zinc-800/80 bg-zinc-950/40 text-[11px] font-mono text-zinc-400">
        <div className="flex items-center space-x-3">
          <span className="flex items-center space-x-1">
            <Cpu className="w-3.5 h-3.5 text-indigo-400" />
            <span>Provider: <strong className="text-zinc-200 font-semibold">{response.provider}</strong></span>
          </span>
          <span>•</span>
          <span>Model: <strong className="text-indigo-300 font-semibold">{response.model}</strong></span>
        </div>

        <div className="flex items-center space-x-1">
          <Clock className="w-3.5 h-3.5 text-amber-400" />
          <span>Latency: <strong className="text-amber-300 font-semibold">{Math.round(response.latency_ms)} ms</strong></span>
        </div>
      </div>
    </div>
  );
}
