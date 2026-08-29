"use client";

import { useState, useEffect } from "react";
import { X, Key, Eye, EyeOff, ShieldAlert, Check } from "lucide-react";
import {
  getStoredApiKey,
  setStoredApiKey,
  clearStoredApiKey,
  getMaskedApiKey,
} from "@/lib/api-client";

interface SettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSaved: () => void;
  authErrorMessage?: string | null;
}

export function SettingsModal({
  isOpen,
  onClose,
  onSaved,
  authErrorMessage,
}: SettingsModalProps) {
  const [apiKeyInput, setApiKeyInput] = useState<string>("");
  const [showKey, setShowKey] = useState<boolean>(false);
  const [currentMasked, setCurrentMasked] = useState<string>("");
  const [isSavedNotice, setIsSavedNotice] = useState<boolean>(false);

  useEffect(() => {
    if (isOpen) {
      const stored = getStoredApiKey();
      setApiKeyInput(stored);
      setCurrentMasked(getMaskedApiKey(stored));
      setIsSavedNotice(false);
    }
  }, [isOpen]);

  if (!isOpen) return null;

  const handleSave = () => {
    setStoredApiKey(apiKeyInput);
    const updated = getStoredApiKey();
    setCurrentMasked(getMaskedApiKey(updated));
    setIsSavedNotice(true);
    setTimeout(() => setIsSavedNotice(false), 2000);
    onSaved();
  };

  const handleClear = () => {
    clearStoredApiKey();
    setApiKeyInput("");
    setCurrentMasked("");
    onSaved();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-[#111111]/80 backdrop-blur-[2px] animate-fade-in-up font-sans">
      <div className="w-full max-w-[440px] bg-[#1C1C1C] border border-[#2A2A2A] rounded-lg overflow-hidden flex flex-col shadow-[0_4px_12px_rgba(0,0,0,0.5)]">
        {/* Header */}
        <div className="p-4 border-b border-[#2A2A2A] flex justify-between items-center bg-[#171717]">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded bg-[#121414] border border-[#2A2A2A] flex items-center justify-center text-[#ffb786]">
              <Key className="w-4 h-4" />
            </div>
            <div>
              <h2 className="text-base font-semibold text-[#e2e2e2]">API Key Configuration</h2>
              <p className="text-xs text-[#8c909f]">Backend security & access authentication</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-[#8c909f] hover:text-[#e2e2e2] p-1 rounded transition-colors cursor-pointer"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Content */}
        <div className="p-5 flex flex-col gap-4">
          {/* Auth Error Banner if present */}
          {authErrorMessage && (
            <div className="p-3 rounded bg-[#93000a]/20 border border-[#ffb4ab]/30 flex items-start gap-2.5 text-xs text-[#ffb4ab]">
              <ShieldAlert className="w-4 h-4 shrink-0 mt-0.5" />
              <div className="space-y-0.5">
                <p className="font-semibold">Authentication Required</p>
                <p>{authErrorMessage}</p>
              </div>
            </div>
          )}

          {/* Current Key Masked Badge */}
          {currentMasked && (
            <div className="flex items-center justify-between px-3 py-2 rounded bg-[#121414] border border-[#2A2A2A] text-xs font-mono">
              <span className="text-[#8c909f]">Active Key:</span>
              <span className="text-[#adc6ff] font-semibold">{currentMasked}</span>
            </div>
          )}

          {/* Key Input */}
          <div className="flex flex-col gap-1.5">
            <label className="text-xs font-medium text-[#e2e2e2]">
              DEVMIND_API_KEY (X-API-Key Header)
            </label>
            <div className="relative">
              <input
                type={showKey ? "text" : "password"}
                value={apiKeyInput}
                onChange={(e) => setApiKeyInput(e.target.value)}
                placeholder="Enter your DevMind API key..."
                className="w-full bg-[#111111] border border-[#2A2A2A] text-[#e2e2e2] text-xs px-3 py-2 pr-9 rounded focus:outline-none focus:border-[#3B82F6] focus:ring-1 focus:ring-[#3B82F6] placeholder-[#8c909f]/50 transition-colors font-mono"
              />
              <button
                type="button"
                onClick={() => setShowKey(!showKey)}
                className="absolute right-2.5 top-2.5 text-[#8c909f] hover:text-[#e2e2e2] transition-colors"
              >
                {showKey ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
              </button>
            </div>
            <p className="text-[11px] text-[#8c909f]">
              Key is stored only in browser <code className="font-mono text-[#adc6ff]">localStorage</code> and sent securely in request headers.
            </p>
          </div>

          {/* Footer Buttons */}
          <div className="flex items-center justify-between pt-2 border-t border-[#2A2A2A]">
            <button
              type="button"
              onClick={handleClear}
              disabled={!currentMasked && !apiKeyInput}
              className="px-2.5 py-1 text-xs text-[#8c909f] hover:text-[#ffb4ab] rounded transition-colors disabled:opacity-30 cursor-pointer"
            >
              Clear Key
            </button>

            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={onClose}
                className="px-3 py-1.5 text-xs text-[#8c909f] hover:text-[#e2e2e2] rounded transition-colors cursor-pointer"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleSave}
                className="flex items-center gap-1.5 px-4 py-1.5 text-xs font-medium bg-[#3B82F6] hover:bg-[#2563eb] text-[#F5F5F5] rounded transition-colors cursor-pointer"
              >
                {isSavedNotice ? (
                  <>
                    <Check className="w-3.5 h-3.5" />
                    <span>Saved!</span>
                  </>
                ) : (
                  <span>Save Key</span>
                )}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
