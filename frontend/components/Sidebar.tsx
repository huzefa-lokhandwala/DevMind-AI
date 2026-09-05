"use client";

import {
  Terminal,
  Plus,
  Database,
  History,
  Settings,
  FolderOpen,
  Radio,
  MessageSquare,
  Trash2,
} from "lucide-react";
import { ConversationSummary } from "@/lib/types";

interface SidebarProps {
  activeRepository: string | null;
  activeView: "chat" | "history";
  conversations?: ConversationSummary[];
  activeConversationId?: string | null;
  onNewChat: () => void;
  onSelectConversation?: (id: string) => void;
  onDeleteConversation?: (id: string) => void;
  onOpenIndexModal: () => void;
  onOpenSettingsModal: () => void;
  onToggleHistory: () => void;
}

export function Sidebar({
  activeRepository,
  activeView,
  conversations = [],
  activeConversationId,
  onNewChat,
  onSelectConversation,
  onDeleteConversation,
  onOpenIndexModal,
  onOpenSettingsModal,
  onToggleHistory,
}: SidebarProps) {
  return (
    <nav className="w-[240px] h-screen border-r border-[#2A2A2A] bg-[#171717] flex flex-col p-4 gap-2 hidden md:flex shrink-0 font-sans select-none">
      {/* Header */}
      <div className="mb-2 pt-1 px-1">
        <div className="flex items-center gap-2.5 mb-1">
          <div className="w-8 h-8 rounded-lg bg-[#1C1C1C] border border-[#2A2A2A] flex items-center justify-center text-[#adc6ff] shrink-0">
            <Terminal className="w-4 h-4" />
          </div>
          <div>
            <h1 className="font-semibold text-sm text-[#e2e2e2] leading-tight">DevMind AI</h1>
            <p className="text-[11px] text-[#8c909f]">Developer Workspace</p>
          </div>
        </div>
      </div>

      {/* New Chat Primary CTA */}
      <button
        onClick={onNewChat}
        className="w-full bg-[#3B82F6] hover:bg-[#2563eb] text-[#F5F5F5] rounded-lg py-2 px-3 flex items-center justify-center gap-2 mb-1 font-medium text-xs transition-colors cursor-pointer active:scale-[0.98] shadow-sm"
      >
        <Plus className="w-4 h-4" />
        <span>New Chat</span>
      </button>

      {/* Main Navigation Items */}
      <div className="flex flex-col gap-1">
        <button
          onClick={onOpenIndexModal}
          className="flex items-center gap-2.5 px-3 py-1.5 rounded-lg text-xs font-medium text-[#a1a1aa] hover:bg-[#1C1C1C] hover:text-[#e2e2e2] transition-colors text-left cursor-pointer"
        >
          <Database className="w-4 h-4 text-[#8c909f]" />
          <span>Repositories</span>
        </button>

        <button
          onClick={onToggleHistory}
          className={`flex items-center gap-2.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors text-left cursor-pointer ${
            activeView === "history"
              ? "bg-[#304671]/40 text-[#adc6ff] border border-[#304671]/60"
              : "text-[#a1a1aa] hover:bg-[#1C1C1C] hover:text-[#e2e2e2]"
          }`}
        >
          <History className="w-4 h-4 text-[#8c909f]" />
          <span>Quick History</span>
        </button>

        <button
          onClick={onOpenSettingsModal}
          className="flex items-center gap-2.5 px-3 py-1.5 rounded-lg text-xs font-medium text-[#a1a1aa] hover:bg-[#1C1C1C] hover:text-[#e2e2e2] transition-colors text-left cursor-pointer"
        >
          <Settings className="w-4 h-4 text-[#8c909f]" />
          <span>Settings</span>
        </button>
      </div>

      {/* Recent Chats Section */}
      <div className="flex-1 min-h-0 flex flex-col mt-2 pt-2 border-t border-[#2A2A2A]">
        <p className="text-[10px] font-mono font-medium text-[#8c909f] px-2 mb-1 uppercase tracking-wider">
          Recent Chats
        </p>

        <div className="flex-1 overflow-y-auto flex flex-col gap-0.5 pr-1">
          {conversations.length === 0 ? (
            <div className="px-2 py-3 text-[11px] text-[#8c909f]/70 font-mono text-center">
              No conversations yet
            </div>
          ) : (
            conversations.map((conv) => {
              const isActive = conv.id === activeConversationId;
              return (
                <div
                  key={conv.id}
                  onClick={() => onSelectConversation && onSelectConversation(conv.id)}
                  className={`group flex items-center justify-between px-2.5 py-1.5 rounded-lg text-xs transition-all cursor-pointer ${
                    isActive
                      ? "bg-[#304671]/40 text-[#adc6ff] border border-[#304671]/60 font-medium"
                      : "text-[#a1a1aa] hover:bg-[#1C1C1C] hover:text-[#e2e2e2]"
                  }`}
                  title={conv.title}
                >
                  <div className="flex items-center gap-2 min-w-0 flex-1">
                    <MessageSquare className="w-3.5 h-3.5 shrink-0 opacity-70" />
                    <span className="truncate text-xs">{conv.title}</span>
                  </div>
                  {onDeleteConversation && (
                    <button
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation();
                        onDeleteConversation(conv.id);
                      }}
                      className="opacity-0 group-hover:opacity-100 p-1 text-[#8c909f] hover:text-[#ffb4ab] transition-opacity cursor-pointer shrink-0 ml-1"
                      title="Delete conversation"
                    >
                      <Trash2 className="w-3 h-3" />
                    </button>
                  )}
                </div>
              );
            })
          )}
        </div>
      </div>

      {/* Active Context Highlight */}
      <div className="pt-2 border-t border-[#2A2A2A]">
        <p className="text-[10px] font-mono font-medium text-[#8c909f] px-2 mb-1 uppercase tracking-wider">
          Active Context
        </p>
        <div
          onClick={onOpenIndexModal}
          className="flex items-center gap-2 px-2.5 py-1.5 bg-[#121414] border border-[#2A2A2A] hover:border-[#3B82F6]/60 rounded-lg text-[#adc6ff] transition-all cursor-pointer group"
          title="Click to switch or index repository"
        >
          <FolderOpen className="w-3.5 h-3.5 text-[#3B82F6] shrink-0" />
          <span className="font-mono text-xs truncate group-hover:text-[#F5F5F5]">
            {activeRepository ? activeRepository : "None (Index repo)"}
          </span>
        </div>
      </div>

      {/* Footer Navigation */}
      <div className="mt-auto pt-2 border-t border-[#2A2A2A] flex flex-col gap-1">
        <button
          onClick={onOpenSettingsModal}
          className="flex items-center gap-2.5 px-3 py-1.5 text-xs text-[#8c909f] hover:bg-[#1C1C1C] hover:text-[#e2e2e2] rounded-lg transition-colors text-left cursor-pointer"
        >
          <Settings className="w-3.5 h-3.5" />
          <span>API Key Config</span>
        </button>
        <div className="flex items-center gap-2.5 px-3 py-1 text-xs text-[#8c909f]">
          <Radio className="w-3.5 h-3.5 text-[#10B981]" />
          <span className="font-mono text-[11px]">RAG V2 Online</span>
        </div>
      </div>
    </nav>
  );
}
