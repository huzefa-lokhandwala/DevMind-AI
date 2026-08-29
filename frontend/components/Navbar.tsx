"use client";

import { StatusBadge } from "./StatusBadge";
import { Terminal, Key, Plus, Menu } from "lucide-react";
import { getMaskedApiKey, getStoredApiKey } from "@/lib/api-client";
import { useEffect, useState } from "react";

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
    <header className="h-[52px] w-full border-b border-[#2A2A2A] bg-[#171717] flex justify-between items-center px-4 md:px-6 shrink-0 z-20 font-sans">
      {/* Left: Mobile Brand & Status */}
      <div className="flex items-center gap-3 md:gap-4">
        {/* Mobile Menu Trigger */}
        <button
          onClick={onToggleMobileMenu}
          className="md:hidden flex items-center justify-center w-8 h-8 rounded-lg hover:bg-[#282a2b] text-[#a1a1aa] transition-colors"
          aria-label="Toggle Navigation"
        >
          <Menu className="w-4 h-4" />
        </button>

        <div className="flex items-center gap-2 md:hidden">
          <div className="w-6 h-6 rounded bg-[#1C1C1C] border border-[#2A2A2A] flex items-center justify-center text-[#adc6ff]">
            <Terminal className="w-3.5 h-3.5" />
          </div>
          <span className="font-semibold text-xs text-[#e2e2e2]">DevMind AI</span>
        </div>

        {/* Live Backend Readiness Status */}
        <StatusBadge />

        {/* Desktop Navigation Links */}
        <nav className="hidden md:flex items-center gap-4 ml-4 font-medium text-xs">
          <span className="text-[#adc6ff] border-b-2 border-[#3B82F6] py-[15px] font-semibold">
            Search
          </span>
          <span className="text-[#8c909f] hover:text-[#e2e2e2] transition-colors py-[15px] cursor-default">
            CodeGraph
          </span>
          <span className="text-[#8c909f] hover:text-[#e2e2e2] transition-colors py-[15px] cursor-default">
            Line Citations
          </span>
        </nav>
      </div>

      {/* Right: Actions */}
      <div className="flex items-center gap-2 md:gap-3">
        {/* Active Repository Pill */}
        {activeRepository && (
          <div className="hidden lg:flex items-center gap-1.5 px-2.5 py-1 rounded border border-[#2A2A2A] bg-[#121414] text-[11px] font-mono text-[#a1a1aa]">
            <span className="text-[#8c909f]">repo:</span>
            <span className="text-[#adc6ff] font-semibold truncate max-w-[140px]">{activeRepository}</span>
          </div>
        )}

        {/* Index Repository Button */}
        <button
          onClick={onOpenIndexModal}
          className="flex items-center gap-1.5 h-8 px-3 bg-[#1C1C1C] border border-[#2A2A2A] text-[#e2e2e2] hover:border-[#a1a1aa] hover:bg-[#282a2b] transition-all rounded text-xs font-medium cursor-pointer shadow-sm active:scale-[0.98]"
        >
          <Plus className="w-3.5 h-3.5 text-[#3B82F6]" />
          <span>Index Repository</span>
        </button>

        {/* Settings / API Key Button */}
        <button
          onClick={onOpenSettingsModal}
          className="flex items-center gap-1.5 h-8 px-3 text-[#a1a1aa] hover:bg-[#282a2b] hover:text-[#e2e2e2] transition-colors rounded text-xs font-mono border border-transparent hover:border-[#2A2A2A]"
          title="Configure X-API-Key"
        >
          <Key className="w-3.5 h-3.5 text-[#ffb786]" />
          <span className="hidden sm:inline">
            {apiKeyMasked ? apiKeyMasked : "API Key"}
          </span>
        </button>
      </div>
    </header>
  );
}
