"use client";

import { useState, useEffect } from "react";
import { Sidebar } from "@/components/Sidebar";
import { Navbar } from "@/components/Navbar";
import { InitialState } from "@/components/InitialState";
import { ConversationView } from "@/components/ConversationView";
import { EvidencePanel } from "@/components/EvidencePanel";
import { IndexModal } from "@/components/IndexModal";
import { SettingsModal } from "@/components/SettingsModal";
import { HistoryDrawer } from "@/components/HistoryDrawer";
import { queryCodebase, AuthError } from "@/lib/api-client";
import { QueryResponse, IndexRepositoryResponse, SourceDocument } from "@/lib/types";

interface ConversationItem {
  query: string;
  response?: QueryResponse;
  error?: string;
}

export default function Home() {
  const [activeRepository, setActiveRepository] = useState<string | null>(null);
  const [conversations, setConversations] = useState<ConversationItem[]>([]);
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

  // Load last active repository or query history if present in localStorage
  useEffect(() => {
    try {
      const savedRepo = localStorage.getItem("devmind_active_repo");
      if (savedRepo) setActiveRepository(savedRepo);
      const savedHistory = localStorage.getItem("devmind_query_history");
      if (savedHistory) setQueryHistory(JSON.parse(savedHistory));
    } catch {
      // ignore storage errors
    }
  }, []);

  const handleIndexSuccess = (res: IndexRepositoryResponse) => {
    setActiveRepository(res.repository);
    try {
      localStorage.setItem("devmind_active_repo", res.repository);
    } catch {}
  };

  const handleSendQuery = async (queryText: string, topK: number) => {
    if (!queryText.trim() || isLoadingQuery) return;

    setIsLoadingQuery(true);
    const newConversations = [...conversations, { query: queryText }];
    setConversations(newConversations);

    // Save to query history
    const updatedHistory = Array.from(new Set([queryText, ...queryHistory])).slice(0, 30);
    setQueryHistory(updatedHistory);
    try {
      localStorage.setItem("devmind_query_history", JSON.stringify(updatedHistory));
    } catch {}

    try {
      const response = await queryCodebase({
        query: queryText,
        top_k: topK,
      });

      setConversations((prev) =>
        prev.map((item, idx) =>
          idx === prev.length - 1 ? { ...item, response } : item
        )
      );

      // Automatically focus first source of this response and open evidence panel
      setSelectedEvidenceIndex(0);
      if (response.sources && response.sources.length > 0) {
        setActiveEvidenceSources(response.sources);
        setIsEvidenceOpen(true);
      }
    } catch (err: any) {
      if (err instanceof AuthError) {
        setAuthErrorMessage(err.message);
        setIsSettingsModalOpen(true);
      }
      setConversations((prev) =>
        prev.map((item, idx) =>
          idx === prev.length - 1
            ? { ...item, error: err.message || "Failed to retrieve codebase answer." }
            : item
        )
      );
    } finally {
      setIsLoadingQuery(false);
    }
  };

  const handleNewChat = () => {
    setConversations([]);
    setActiveEvidenceSources([]);
    setSelectedEvidenceIndex(0);
  };

  const handleClearHistory = () => {
    setQueryHistory([]);
    try {
      localStorage.removeItem("devmind_query_history");
    } catch {}
  };

  return (
    <div className="flex h-screen w-full overflow-hidden bg-[#111111] text-[#e2e2e2] font-sans antialiased">
      {/* Left Sidebar */}
      <Sidebar
        activeRepository={activeRepository}
        activeView={conversations.length > 0 ? "chat" : "chat"}
        onNewChat={handleNewChat}
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

              {/* Right Side Evidence Inspector Panel */}
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
