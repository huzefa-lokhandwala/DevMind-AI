"use client";

import { useState, useEffect, useCallback } from "react";
import { Sidebar } from "@/components/Sidebar";
import { Navbar } from "@/components/Navbar";
import { InitialState } from "@/components/InitialState";
import { ConversationView } from "@/components/ConversationView";
import { EvidencePanel } from "@/components/EvidencePanel";
import { IndexModal } from "@/components/IndexModal";
import { SettingsModal } from "@/components/SettingsModal";
import { HistoryDrawer } from "@/components/HistoryDrawer";
import {
  queryCodebase,
  listConversations,
  getConversation,
  deleteConversation,
  clearAllConversations,
  AuthError,
} from "@/lib/api-client";
import {
  QueryResponse,
  IndexRepositoryResponse,
  SourceDocument,
  ConversationSummary,
} from "@/lib/types";

interface ConversationItem {
  query: string;
  response?: QueryResponse;
  error?: string;
}

export default function Home() {
  const [activeRepository, setActiveRepository] = useState<string | null>(null);
  const [conversations, setConversations] = useState<ConversationItem[]>([]);
  const [activeConversationId, setActiveConversationId] = useState<string | null>(null);
  const [savedConversations, setSavedConversations] = useState<ConversationSummary[]>([]);
  const [queryHistory, setQueryHistory] = useState<string[]>([]);
  const [isLoadingQuery, setIsLoadingQuery] = useState<boolean>(false);
  const [activeEvidenceSources, setActiveEvidenceSources] = useState<SourceDocument[]>([]);
  const [selectedEvidenceIndex, setSelectedEvidenceIndex] = useState<number>(0);
  const [isEvidenceOpen, setIsEvidenceOpen] = useState<boolean>(true);

  // Modals
  const [isIndexModalOpen, setIsIndexModalOpen] = useState<boolean>(false);
  const [isSettingsModalOpen, setIsSettingsModalOpen] = useState<boolean>(false);
  const [isHistoryOpen, setIsHistoryOpen] = useState<boolean>(false);
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState<boolean>(false);
  const [authErrorMessage, setAuthErrorMessage] = useState<string | null>(null);

  // Refresh recent conversations from backend
  const refreshConversationsList = useCallback(async () => {
    try {
      const list = await listConversations();
      setSavedConversations(list);
    } catch {
      // ignore network errors on background refresh
    }
  }, []);

  // Load initial settings and saved conversations on mount
  useEffect(() => {
    try {
      const savedRepo = localStorage.getItem("devmind_active_repo");
      if (savedRepo) setActiveRepository(savedRepo);
      const savedHistory = localStorage.getItem("devmind_query_history");
      if (savedHistory) setQueryHistory(JSON.parse(savedHistory));
    } catch {
      // ignore storage errors
    }
    refreshConversationsList();
  }, [refreshConversationsList]);

  const handleIndexSuccess = (res: IndexRepositoryResponse) => {
    setActiveRepository(res.repository);
    try {
      localStorage.setItem("devmind_active_repo", res.repository);
    } catch {}
  };

  const handleSelectConversation = async (conversationId: string) => {
    if (isLoadingQuery) return;
    try {
      const detail = await getConversation(conversationId);
      setActiveConversationId(detail.id);
      if (detail.repository_name) {
        setActiveRepository(detail.repository_name);
      }

      // Reconstruct conversation turn pairs from message records
      const reconstructed: ConversationItem[] = [];
      const messages = detail.messages || [];

      for (let i = 0; i < messages.length; i++) {
        const msg = messages[i];
        if (msg.role === "user") {
          const nextMsg = messages[i + 1];
          if (nextMsg && nextMsg.role === "assistant") {
            reconstructed.push({
              query: msg.content,
              response: {
                answer: nextMsg.content,
                sources: nextMsg.sources || [],
                provider: nextMsg.provider || "gemini",
                model: nextMsg.model || "gemini-3.6-flash",
                latency_ms: nextMsg.latency_ms || 0,
                intent: nextMsg.intent || "REPOSITORY",
                conversation_id: detail.id,
              },
            });
            i++; // skip assistant turn
          } else {
            reconstructed.push({ query: msg.content });
          }
        }
      }

      setConversations(reconstructed);

      // Restore evidence sources from the latest assistant response
      const lastTurn = reconstructed[reconstructed.length - 1];
      if (lastTurn?.response?.sources && lastTurn.response.sources.length > 0) {
        setActiveEvidenceSources(lastTurn.response.sources);
        setSelectedEvidenceIndex(0);
        setIsEvidenceOpen(true);
      } else {
        setActiveEvidenceSources([]);
      }
    } catch (err: any) {
      if (err instanceof AuthError) {
        setAuthErrorMessage(err.message);
        setIsSettingsModalOpen(true);
      }
    }
  };

  const handleDeleteConversation = async (conversationId: string) => {
    try {
      await deleteConversation(conversationId);
      setSavedConversations((prev) => prev.filter((c) => c.id !== conversationId));
      if (activeConversationId === conversationId) {
        handleNewChat();
      }
    } catch (err: any) {
      if (err instanceof AuthError) {
        setAuthErrorMessage(err.message);
        setIsSettingsModalOpen(true);
      }
    }
  };

  const handleSendQuery = async (queryText: string, topK: number) => {
    if (!queryText.trim() || isLoadingQuery) return;

    setIsLoadingQuery(true);
    const newConversations = [...conversations, { query: queryText }];
    setConversations(newConversations);

    // Save to local quick history
    const updatedHistory = Array.from(new Set([queryText, ...queryHistory])).slice(0, 30);
    setQueryHistory(updatedHistory);
    try {
      localStorage.setItem("devmind_query_history", JSON.stringify(updatedHistory));
    } catch {}

    try {
      const response = await queryCodebase({
        query: queryText,
        top_k: topK,
        conversation_id: activeConversationId || undefined,
      });

      setConversations((prev) =>
        prev.map((item, idx) =>
          idx === prev.length - 1 ? { ...item, response } : item
        )
      );

      if (response.conversation_id) {
        setActiveConversationId(response.conversation_id);
      }

      // Update active evidence sources if available
      if (response.sources && response.sources.length > 0) {
        setSelectedEvidenceIndex(0);
        setActiveEvidenceSources(response.sources);
        setIsEvidenceOpen(true);
      } else {
        setActiveEvidenceSources([]);
      }

      // Refresh sidebar recent conversations
      refreshConversationsList();
    } catch (err: any) {
      if (err instanceof AuthError) {
        setAuthErrorMessage(err.message);
        setIsSettingsModalOpen(true);
      }
      setConversations((prev) =>
        prev.map((item, idx) =>
          idx === prev.length - 1
            ? { ...item, error: err.message || "Failed to retrieve answer." }
            : item
        )
      );
    } finally {
      setIsLoadingQuery(false);
    }
  };

  const handleNewChat = () => {
    setConversations([]);
    setActiveConversationId(null);
    setActiveEvidenceSources([]);
    setSelectedEvidenceIndex(0);
  };

  const handleClearHistory = () => {
    setQueryHistory([]);
    try {
      localStorage.removeItem("devmind_query_history");
    } catch {}
    clearAllConversations().catch(() => {});
    setSavedConversations([]);
  };

  return (
    <div className="flex h-screen w-full overflow-hidden bg-[#111111] text-[#e2e2e2] font-sans antialiased">
      {/* Left Sidebar with Persistent Recent Chats */}
      <Sidebar
        activeRepository={activeRepository}
        activeView="chat"
        conversations={savedConversations}
        activeConversationId={activeConversationId}
        onNewChat={handleNewChat}
        onSelectConversation={handleSelectConversation}
        onDeleteConversation={handleDeleteConversation}
        onOpenIndexModal={() => setIsIndexModalOpen(true)}
        onOpenSettingsModal={() => setIsSettingsModalOpen(true)}
        onToggleHistory={() => setIsHistoryOpen(true)}
      />

      {/* Main Workspace Column */}
      <div className="flex-1 flex flex-col min-w-0 h-full relative overflow-hidden">
        {/* Top Navbar */}
        <Navbar
          activeRepository={activeRepository}
          onOpenIndexModal={() => setIsIndexModalOpen(true)}
          onOpenSettingsModal={() => setIsSettingsModalOpen(true)}
          onToggleMobileMenu={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
        />

        {/* Workspace Canvas */}
        <div className="flex-1 flex flex-col lg:flex-row overflow-hidden w-full relative">
          {conversations.length === 0 ? (
            <InitialState
              activeRepository={activeRepository}
              onSubmit={handleSendQuery}
              isLoading={isLoadingQuery}
            />
          ) : (
            <>
              {/* Central Conversation Canvas */}
              <div className="flex-1 flex flex-col min-w-0 h-full overflow-hidden relative">
                {/* Evidence Panel Re-open Pill (if closed and sources available) */}
                {!isEvidenceOpen && activeEvidenceSources.length > 0 && (
                  <div className="absolute top-3 right-4 z-20 animate-fade-in-up">
                    <button
                      type="button"
                      onClick={() => setIsEvidenceOpen(true)}
                      className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-[#182338] hover:bg-[#304671] text-[#adc6ff] border border-[#3B82F6]/50 shadow-md text-xs font-mono transition-all cursor-pointer"
                      title="Open Evidence Inspector"
                    >
                      <span>Inspect Evidence ({activeEvidenceSources.length})</span>
                    </button>
                  </div>
                )}

                <ConversationView
                  conversations={conversations}
                  isLoading={isLoadingQuery}
                  onSendQuery={handleSendQuery}
                  onSelectEvidence={(idx, sources) => {
                    setSelectedEvidenceIndex(idx);
                    setActiveEvidenceSources(sources);
                    setIsEvidenceOpen(true);
                  }}
                  selectedEvidenceIndex={selectedEvidenceIndex}
                />
              </div>

              {/* Right Side Evidence Inspector Panel (Rendered only when active sources exist) */}
              {isEvidenceOpen && activeEvidenceSources.length > 0 && (
                <EvidencePanel
                  sources={activeEvidenceSources}
                  selectedSourceIndex={selectedEvidenceIndex}
                  onSelectSource={(idx) => setSelectedEvidenceIndex(idx)}
                  onClose={() => setIsEvidenceOpen(false)}
                />
              )}
            </>
          )}
        </div>
      </div>

      {/* Index Repository Modal */}
      <IndexModal
        isOpen={isIndexModalOpen}
        onClose={() => setIsIndexModalOpen(false)}
        onSuccess={handleIndexSuccess}
        onAuthRequired={(msg) => {
          setAuthErrorMessage(msg);
          setIsSettingsModalOpen(true);
        }}
      />

      {/* Settings / API Key Modal */}
      <SettingsModal
        isOpen={isSettingsModalOpen}
        onClose={() => {
          setIsSettingsModalOpen(false);
          setAuthErrorMessage(null);
        }}
        onSaved={() => {
          setIsSettingsModalOpen(false);
          setAuthErrorMessage(null);
        }}
        authErrorMessage={authErrorMessage}
      />

      {/* Query History Drawer */}
      <HistoryDrawer
        isOpen={isHistoryOpen}
        onClose={() => setIsHistoryOpen(false)}
        history={queryHistory}
        onSelectQuery={(q) => handleSendQuery(q, 5)}
        onClearHistory={handleClearHistory}
      />
    </div>
  );
}
