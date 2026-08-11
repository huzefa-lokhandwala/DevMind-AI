"use client";

import { useState, useEffect } from "react";
import { X, Key, Eye, EyeOff, ShieldAlert, Check } from "lucide-react";
import { getStoredApiKey, setStoredApiKey, clearStoredApiKey, getMaskedApiKey } from "@/lib/api-client";

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
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="w-full max-w-md bg-zinc-900 border border-zinc-800 rounded-xl shadow-2xl overflow-hidden font-sans">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-zinc-800 bg-zinc-950/50">
          <div className="flex items-center space-x-2.5">
            <div className="p-2 rounded-lg bg-amber-500/10 text-amber-400 border border-amber-500/20">
              <Key className="w-4 h-4" />
            </div>
            <div>
              <h3 className="text-sm font-semibold text-zinc-100 font-mono">Backend Security Settings</h3>
              <p className="text-xs text-zinc-400">Configure client X-API-Key authorization</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-md text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 space-y-4">
          {/* Auth Error Banner */}
          {authErrorMessage && (
            <div className="p-3 rounded-lg bg-rose-500/10 border border-rose-500/30 flex items-start space-x-2.5">
              <ShieldAlert className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
              <div className="text-xs text-rose-300 space-y-1">
                <p className="font-semibold">Authentication Required</p>
                <p>{authErrorMessage}</p>
              </div>
            </div>
          )}

          {/* Current Key Masked Badge */}
          {currentMasked && (
            <div className="flex items-center justify-between px-3 py-2 rounded-md bg-zinc-950 border border-zinc-800 text-xs font-mono">
              <span className="text-zinc-400">Active Key:</span>
              <span className="font-semibold text-amber-300">{currentMasked}</span>
            </div>
          )}

          {/* Key Input */}
          <div className="space-y-1.5">
            <label className="block text-xs font-mono font-medium text-zinc-300">
              API Key (DEVMIND_API_KEY)
            </label>
            <div className="relative">
              <input
                type={showKey ? "text" : "password"}
                value={apiKeyInput}
                onChange={(e) => setApiKeyInput(e.target.value)}
                placeholder="Enter your DevMind API key..."
                className="w-full px-3 py-2 pr-10 rounded-md bg-zinc-950 border border-zinc-800 text-zinc-100 text-sm font-mono placeholder:text-zinc-600 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition-all"
              />
              <button
                type="button"
                onClick={() => setShowKey(!showKey)}
                className="absolute right-2.5 top-2.5 text-zinc-500 hover:text-zinc-300"
              >
                {showKey ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              </button>
            </div>
            <p className="text-[11px] text-zinc-500">
              Key is stored in browser <code className="text-zinc-400 font-mono">localStorage</code> only and sent via <code className="text-zinc-400 font-mono">X-API-Key</code> request headers.
            </p>
          </div>

          {/* Action Buttons */}
          <div className="flex items-center justify-between pt-2">
            <button
              type="button"
              onClick={handleClear}
              disabled={!currentMasked && !apiKeyInput}
              className="px-3 py-1.5 rounded-md border border-zinc-800 text-zinc-400 hover:text-rose-400 hover:border-rose-900/50 hover:bg-rose-950/20 text-xs font-mono transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
            >
              Clear Key
            </button>

            <div className="flex items-center space-x-2">
              <button
                type="button"
                onClick={onClose}
                className="px-3.5 py-1.5 rounded-md text-zinc-400 hover:text-zinc-200 text-xs font-mono transition-colors"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleSave}
                className="flex items-center space-x-1.5 px-4 py-1.5 rounded-md bg-indigo-600 hover:bg-indigo-500 text-white font-mono text-xs font-medium transition-colors shadow-sm"
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
