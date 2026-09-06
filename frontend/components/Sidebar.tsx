"use client";

import React from "react";
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
  ChevronRight,
  FolderGit2,
} from "lucide-react";
import { ConversationSummary } from "@/lib/types";
import { UserMenu } from "./UserMenu";

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
  userName?: string;
  userEmail?: string;
  onLogout?: () => void;
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
  userName = "Developer Workspace",
  userEmail = "dev@workspace.local",
  onLogout,
}: SidebarProps) {
  // Categorize conversations chronologically if timestamps are available
  return (
    <nav
      aria-label="Workspace sidebar"
      className="w-[250px] h-screen border-r border-[#1f242d] bg-[#0c0e12] flex flex-col p-3.5 gap-2 hidden md:flex shrink-0 font-sans select-none"
    >
      {/* DevMind Brand Header */}
      <div className="mb-1 px-1 pt-1">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-[#14171d] border border-[#222834] flex items-center justify-center text-[#adc6ff] shrink-0 shadow-sm">
            <Terminal className="w-4 h-4 text-[#3b82f6]" />
          </div>
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-1.5">
              <h1 className="font-semibold text-sm text-[#f3f4f6] leading-tight truncate">
                DevMind AI
              </h1>
            </div>
            <p className="text-[11px] text-[#6b7280] font-mono truncate">
              Code Intelligence
            </p>
          </div>
        </div>
      </div>

      {/* New Chat Primary Action */}
      <button
        type="button"
        onClick={onNewChat}
        className="w-full bg-[#3b82f6] hover:bg-[#2563eb] text-white rounded-lg py-2 px-3 flex items-center justify-center gap-2 mb-1 font-medium text-xs transition-all cursor-pointer active:scale-[0.98] shadow-sm"
      >
        <Plus className="w-4 h-4" />
        <span>New Conversation</span>
      </button>

      {/* Main Workspace Navigation */}
      <div className="flex flex-col gap-0.5">
        <button
          type="button"
          onClick={onOpenIndexModal}
          className="flex items-center justify-between px-2.5 py-1.5 rounded-lg text-xs font-medium text-[#9ca3af] hover:bg-[#14171d] hover:text-[#f3f4f6] transition-colors text-left cursor-pointer group"
        >
          <div className="flex items-center gap-2.5">
            <Database className="w-3.5 h-3.5 text-[#6b7280] group-hover:text-[#3b82f6] transition-colors" />
            <span>Repositories</span>
          </div>
          <ChevronRight className="w-3 h-3 text-[#4b5563] group-hover:text-[#9ca3af] transition-colors" />
        </button>

        <button
          type="button"
          onClick={onToggleHistory}
          className={`flex items-center justify-between px-2.5 py-1.5 rounded-lg text-xs font-medium transition-colors text-left cursor-pointer group ${
            activeView === "history"
              ? "bg-[#182338] text-[#adc6ff] border border-[#3b82f6]/40"
              : "text-[#9ca3af] hover:bg-[#14171d] hover:text-[#f3f4f6]"
          }`}
        >
          <div className="flex items-center gap-2.5">
            <History className="w-3.5 h-3.5 text-[#6b7280] group-hover:text-[#3b82f6] transition-colors" />
            <span>Quick Queries</span>
          </div>
          <ChevronRight className="w-3 h-3 text-[#4b5563] group-hover:text-[#9ca3af] transition-colors" />
        </button>

        <button
          type="button"
          onClick={onOpenSettingsModal}
          className="flex items-center justify-between px-2.5 py-1.5 rounded-lg text-xs font-medium text-[#9ca3af] hover:bg-[#14171d] hover:text-[#f3f4f6] transition-colors text-left cursor-pointer group"
        >
          <div className="flex items-center gap-2.5">
            <Settings className="w-3.5 h-3.5 text-[#6b7280] group-hover:text-[#3b82f6] transition-colors" />
            <span>Settings</span>
          </div>
          <ChevronRight className="w-3 h-3 text-[#4b5563] group-hover:text-[#9ca3af] transition-colors" />
        </button>
      </div>

      {/* Active Repository Context Card */}
      <div className="pt-2 border-t border-[#1a1e27]">
        <div className="flex items-center justify-between px-1 mb-1 text-[10px] font-mono text-[#6b7280] uppercase tracking-wider">
          <span>Target Context</span>
          <span className="text-[#3b82f6]">Active</span>
        </div>
        <div
          onClick={onOpenIndexModal}
          className="flex items-center gap-2 px-2.5 py-2 bg-[#101317] border border-[#1e232d] hover:border-[#3b82f6]/50 rounded-lg text-[#adc6ff] transition-all cursor-pointer group"
          title="Click to switch or index repository"
        >
          <FolderGit2 className="w-4 h-4 text-[#3b82f6] shrink-0" />
          <div className="min-w-0 flex-1">
            <p className="font-mono text-xs text-[#e2e8f0] truncate group-hover:text-white">
              {activeRepository ? activeRepository : "None selected"}
            </p>
            <p className="text-[10px] text-[#6b7280] font-mono truncate">
              {activeRepository ? "Indexed · 768d RAG" : "Click to index repo"}
            </p>
          </div>
        </div>
      </div>

      {/* Recent Conversations */}
      <div className="flex-1 min-h-0 flex flex-col mt-2 pt-2 border-t border-[#1a1e27]">
        <p className="text-[10px] font-mono font-medium text-[#6b7280] px-1 mb-1.5 uppercase tracking-wider">
          Recent Conversations
        </p>

        <div className="flex-1 overflow-y-auto flex flex-col gap-0.5 pr-0.5 scrollbar-thin">
          {conversations.length === 0 ? (
            <div className="px-2 py-4 text-[11px] text-[#6b7280] font-mono text-center">
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
                      ? "bg-[#182338] text-[#adc6ff] border border-[#3b82f6]/40 font-medium shadow-sm"
                      : "text-[#9ca3af] hover:bg-[#14171d] hover:text-[#f3f4f6]"
                  }`}
                  title={conv.title}
                >
                  <div className="flex items-center gap-2 min-w-0 flex-1">
                    <MessageSquare className={`w-3.5 h-3.5 shrink-0 ${isActive ? "text-[#3b82f6]" : "opacity-70"}`} />
                    <span className="truncate text-xs">{conv.title}</span>
                  </div>
                  {onDeleteConversation && (
                    <button
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation();
                        onDeleteConversation(conv.id);
                      }}
                      className="opacity-0 group-hover:opacity-100 p-1 text-[#6b7280] hover:text-[#f87171] transition-opacity cursor-pointer shrink-0 ml-1"
                      title="Delete conversation"
                      aria-label={`Delete conversation ${conv.title}`}
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

      {/* User Profile & Engine Status Footer */}
      <div className="mt-auto pt-2 border-t border-[#1a1e27] flex flex-col gap-1.5">
        <UserMenu
          userName={userName}
          userEmail={userEmail}
          onOpenSettings={onOpenSettingsModal}
          onLogout={onLogout}
        />
        <div className="flex items-center justify-between px-2 pt-0.5 text-[11px] text-[#6b7280] font-mono">
          <div className="flex items-center gap-1.5">
            <Radio className="w-3 h-3 text-[#10b981]" />
            <span>RAG Online</span>
          </div>
          <span className="text-[#4b5563]">Gemini 768d</span>
        </div>
      </div>
    </nav>
  );
}
