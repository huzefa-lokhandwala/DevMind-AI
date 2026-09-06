"use client";

import React, { useEffect, useState } from "react";
import { StatusBadge } from "./StatusBadge";
import { Terminal, Key, Plus, Menu, FolderGit2, Sparkles } from "lucide-react";
import { getMaskedApiKey, getStoredApiKey } from "@/lib/api-client";

interface NavbarProps {
  activeRepository: string | null;
  onOpenIndexModal: () => void;
  onOpenSettingsModal: () => void;
  onToggleMobileMenu?: () => void;
}

export function Navbar({
  activeRepository,
  onOpenIndexModal,
  onOpenSettingsModal,
  onToggleMobileMenu,
}: NavbarProps) {
  const [apiKeyMasked, setApiKeyMasked] = useState<string>("");

  useEffect(() => {
    const key = getStoredApiKey();
    setApiKeyMasked(getMaskedApiKey(key));
  }, []);

  return (
    <header className="h-[52px] w-full border-b border-[#1f242d] bg-[#0c0e12] flex justify-between items-center px-4 md:px-6 shrink-0 z-20 font-sans select-none">
      {/* Left: Mobile Brand & System Health */}
      <div className="flex items-center gap-3 md:gap-4">
        {/* Mobile Menu Trigger */}
        <button
          type="button"
          onClick={onToggleMobileMenu}
          className="md:hidden flex items-center justify-center w-8 h-8 rounded-lg hover:bg-[#161a22] text-[#9ca3af] transition-colors"
          aria-label="Toggle Navigation"
        >
          <Menu className="w-4 h-4" />
        </button>

        <div className="flex items-center gap-2 md:hidden">
          <div className="w-6 h-6 rounded bg-[#14171d] border border-[#222834] flex items-center justify-center text-[#adc6ff]">
            <Terminal className="w-3.5 h-3.5 text-[#3b82f6]" />
          </div>
          <span className="font-semibold text-xs text-[#f3f4f6]">DevMind AI</span>
        </div>

        {/* Live Backend Readiness Status */}
        <StatusBadge />

        {/* Mode Indicators */}
        <div className="hidden lg:flex items-center gap-2 font-mono text-[11px] text-[#6b7280]">
          <span>·</span>
          <span>AST Chunking</span>
          <span>·</span>
          <span>pgvector 768d</span>
        </div>
      </div>

      {/* Right: Repository Context & Actions */}
      <div className="flex items-center gap-2 md:gap-3">
        {/* Active Repository Pill */}
        {activeRepository ? (
          <div
            onClick={onOpenIndexModal}
            className="hidden sm:flex items-center gap-1.5 px-2.5 py-1 rounded-md border border-[#1e232d] bg-[#101317] hover:border-[#3b82f6]/50 text-[11px] font-mono text-[#9ca3af] transition-colors cursor-pointer"
            title="Active indexed repository"
          >
            <FolderGit2 className="w-3.5 h-3.5 text-[#3b82f6]" />
            <span className="text-[#6b7280]">repo:</span>
            <span className="text-[#adc6ff] font-medium truncate max-w-[140px]">
              {activeRepository}
            </span>
          </div>
        ) : (
          <div className="hidden sm:flex items-center gap-1.5 px-2.5 py-1 rounded-md border border-[#222834] bg-[#0e1115] text-[11px] font-mono text-[#6b7280]">
            <span>No repo selected</span>
          </div>
        )}

        {/* Index Repository Button */}
        <button
          type="button"
          onClick={onOpenIndexModal}
          className="flex items-center gap-1.5 h-8 px-3 bg-[#161a22] border border-[#222834] text-[#f3f4f6] hover:border-[#3b82f6]/50 hover:bg-[#1b202a] transition-all rounded-md text-xs font-medium cursor-pointer shadow-sm active:scale-[0.98]"
        >
          <Plus className="w-3.5 h-3.5 text-[#3b82f6]" />
          <span className="hidden sm:inline">Index Repository</span>
          <span className="sm:hidden">Index</span>
        </button>

        {/* Settings / API Key Button */}
        <button
          type="button"
          onClick={onOpenSettingsModal}
          className="flex items-center gap-1.5 h-8 px-2.5 text-[#9ca3af] hover:bg-[#161a22] hover:text-[#f3f4f6] transition-colors rounded-md text-xs font-mono border border-transparent hover:border-[#222834] cursor-pointer"
          title="Configure API key and view settings"
        >
          <Key className="w-3.5 h-3.5 text-[#f59e0b]" />
          <span className="hidden md:inline">
            {apiKeyMasked ? apiKeyMasked : "API Key"}
          </span>
        </button>
      </div>
    </header>
  );
}
