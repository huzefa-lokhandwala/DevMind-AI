"use client";

import { X, History, ArrowRight, Trash2 } from "lucide-react";

interface HistoryDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  history: string[];
  onSelectQuery: (query: string) => void;
  onClearHistory: () => void;
}

export function HistoryDrawer({
  isOpen,
  onClose,
  history,
  onSelectQuery,
  onClearHistory,
}: HistoryDrawerProps) {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-[#111111]/80 backdrop-blur-[2px] animate-fade-in-up font-sans">
      <div className="w-full max-w-[480px] bg-[#1C1C1C] border border-[#2A2A2A] rounded-lg overflow-hidden flex flex-col shadow-[0_4px_12px_rgba(0,0,0,0.5)]">
        {/* Header */}
        <div className="p-4 border-b border-[#2A2A2A] flex justify-between items-center bg-[#171717]">
          <div className="flex items-center gap-2">
            <History className="w-4 h-4 text-[#adc6ff]" />
            <h2 className="text-base font-semibold text-[#e2e2e2]">Query History</h2>
          </div>
          <button
            onClick={onClose}
            className="text-[#8c909f] hover:text-[#e2e2e2] p-1 rounded transition-colors cursor-pointer"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Content */}
        <div className="p-4 max-h-[360px] overflow-y-auto flex flex-col gap-2">
          {history.length === 0 ? (
            <div className="p-8 text-center text-xs text-[#8c909f] font-mono">
              No queries submitted yet in this session.
            </div>
          ) : (
            history.slice().reverse().map((item, idx) => (
              <button
                key={idx}
                onClick={() => {
                  onSelectQuery(item);
                  onClose();
                }}
                className="flex items-center justify-between p-3 rounded-lg bg-[#171717] border border-[#2A2A2A] hover:border-[#3B82F6]/60 hover:bg-[#282a2b] transition-all text-left text-xs text-[#e2e2e2] group cursor-pointer"
              >
                <span className="truncate pr-2 font-mono">{item}</span>
                <ArrowRight className="w-3.5 h-3.5 text-[#8c909f] group-hover:text-[#adc6ff] shrink-0 transition-colors" />
              </button>
            ))
          )}
        </div>

        {/* Footer */}
        {history.length > 0 && (
          <div className="p-3 border-t border-[#2A2A2A] bg-[#171717] flex justify-between items-center text-xs">
            <button
              onClick={onClearHistory}
              className="flex items-center gap-1.5 text-[#8c909f] hover:text-[#ffb4ab] px-2 py-1 rounded transition-colors cursor-pointer"
            >
              <Trash2 className="w-3.5 h-3.5" />
              <span>Clear History</span>
            </button>
            <button
              onClick={onClose}
              className="px-3 py-1 bg-[#282a2b] hover:bg-[#333535] text-[#e2e2e2] rounded transition-colors cursor-pointer"
            >
              Close
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
