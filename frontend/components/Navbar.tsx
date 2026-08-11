"use client";

import { StatusBadge } from "./StatusBadge";
import { Terminal, FolderGit2, Key, Plus } from "lucide-react";
import { getMaskedApiKey, getStoredApiKey } from "@/lib/api-client";
import { useEffect, useState } from "react";

interface NavbarProps {
  activeRepository: string | null;
  onOpenIndexModal: () => void;
  onOpenSettingsModal: () => void;
}

export function Navbar({
  activeRepository,
  onOpenIndexModal,
  onOpenSettingsModal,
}: NavbarProps) {
  const [apiKeyMasked, setApiKeyMasked] = useState<string>("");

  useEffect(() => {
    const key = getStoredApiKey();
    setApiKeyMasked(getMaskedApiKey(key));
  }, []);

  return (
    <header className="sticky top-0 z-30 border-b border-zinc-800 bg-zinc-950/90 backdrop-blur-md px-4 py-3 sm:px-6">
      <div className="max-w-7xl mx-auto flex items-center justify-between">
        {/* Brand Header */}
        <div className="flex items-center space-x-3">
          <div className="p-2 rounded-lg bg-indigo-950/60 border border-indigo-500/30 text-indigo-400">
            <Terminal className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <span className="font-bold text-zinc-100 text-lg tracking-tight font-mono">
                DevMind AI
              </span>
              <span className="px-1.5 py-0.5 text-[10px] font-mono font-semibold rounded bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
                RAG V2
              </span>
            </div>
            <p className="text-xs text-zinc-500 hidden sm:block">
              Codebase Intelligence & AST Hybrid Retrieval
            </p>
          </div>
        </div>

        {/* Status and Action Controls */}
        <div className="flex items-center space-x-3">
          <StatusBadge />

          {/* Active Repository Badge */}
          {activeRepository ? (
            <div className="hidden md:flex items-center space-x-1.5 px-3 py-1 rounded-md border border-zinc-800 bg-zinc-900 text-xs font-mono text-zinc-300">
              <FolderGit2 className="w-3.5 h-3.5 text-indigo-400" />
              <span className="text-zinc-400">repo:</span>
              <span className="font-semibold text-indigo-300">{activeRepository}</span>
            </div>
          ) : null}

          {/* Index Repository Button */}
          <button
            onClick={onOpenIndexModal}
            className="flex items-center space-x-1.5 px-3 py-1.5 rounded-md bg-indigo-600 hover:bg-indigo-500 text-white font-mono text-xs font-medium transition-colors shadow-sm shadow-indigo-900/40"
          >
            <Plus className="w-4 h-4" />
            <span className="hidden sm:inline">Index Repo</span>
          </button>

          {/* Settings / API Key Button */}
          <button
            onClick={onOpenSettingsModal}
            className="flex items-center space-x-1.5 px-3 py-1.5 rounded-md border border-zinc-800 bg-zinc-900 hover:bg-zinc-800 text-zinc-300 text-xs font-mono transition-colors"
            title="Configure X-API-Key"
          >
            <Key className="w-3.5 h-3.5 text-amber-400" />
            <span className="hidden lg:inline text-zinc-400">
              {apiKeyMasked ? apiKeyMasked : "API Key"}
            </span>
          </button>
        </div>
      </div>
    </header>
  );
}
