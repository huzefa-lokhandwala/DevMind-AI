"use client";

import { useState, useEffect } from "react";
import { Navbar } from "@/components/Navbar";
import { IndexModal } from "@/components/IndexModal";
import { SettingsModal } from "@/components/SettingsModal";
import { QueryInput } from "@/components/QueryInput";
import { AnswerView } from "@/components/AnswerView";
import { SourceDrawer } from "@/components/SourceDrawer";
import { queryCodebase, getStoredApiKey, AuthError } from "@/lib/api-client";
import { IndexRepositoryResponse, QueryResponse } from "@/lib/types";
import { Terminal, ShieldAlert, Sparkles, Code2, Layers, Cpu } from "lucide-react";

export default function Home() {
  const [activeRepository, setActiveRepository] = useState<string | null>("proofos");
  const [isIndexModalOpen, setIsIndexModalOpen] = useState<boolean>(false);
  const [isSettingsModalOpen, setIsSettingsModalOpen] = useState<boolean>(false);
  const [authErrorMessage, setAuthErrorMessage] = useState<string | null>(null);

  const [isLoadingQuery, setIsLoadingQuery] = useState<boolean>(false);
  const [queryResponse, setQueryResponse] = useState<QueryResponse | null>(null);
  const [queryError, setQueryError] = useState<string | null>(null);
  const [queryHistory, setQueryHistory] = useState<string[]>([]);

  useEffect(() => {
    // Check if API key is unconfigured on initial load
    const apiKey = getStoredApiKey();
    if (!apiKey) {
      // Prompt user politely via settings if key is empty
    }
  }, []);

  const handleIndexSuccess = (res: IndexRepositoryResponse) => {
    setActiveRepository(res.repository);
    setIsIndexModalOpen(false);
  };

  const handleAuthRequired = (message: string) => {
    setAuthErrorMessage(message);
    setIsSettingsModalOpen(true);
  };

  const handleQuerySubmit = async (queryStr: string, topK: number) => {
    setIsLoadingQuery(true);
    setQueryError(null);
    setAuthErrorMessage(null);

    try {
      const res = await queryCodebase({ query: queryStr, top_k: topK });
      setQueryResponse(res);
      setIsLoadingQuery(false);

      // Add to query history
      if (!queryHistory.includes(queryStr)) {
        setQueryHistory((prev) => [...prev, queryStr]);
      }
    } catch (err: any) {
      setIsLoadingQuery(false);
      if (err instanceof AuthError) {
        handleAuthRequired(err.message);
        return;
      }
      setQueryError(err.message || "An unexpected error occurred during query processing.");
    }
  };

  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-100 flex flex-col font-sans selection:bg-indigo-500/30 selection:text-indigo-200">
      {/* Navbar Header */}
      <Navbar
        activeRepository={activeRepository}
        onOpenIndexModal={() => setIsIndexModalOpen(true)}
        onOpenSettingsModal={() => setIsSettingsModalOpen(true)}
      />

      {/* Main Workspace Area */}
      <main className="flex-1 max-w-5xl w-full mx-auto px-4 py-8 space-y-6">
        {/* Error Banner */}
        {queryError && (
          <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/30 flex items-start space-x-3 text-xs font-mono text-rose-300 animate-in fade-in duration-150">
            <ShieldAlert className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
            <div className="space-y-1">
              <p className="font-semibold text-rose-200">Query Processing Error</p>
              <p>{queryError}</p>
            </div>
          </div>
        )}

        {/* Natural Language Query Input Section */}
        <section className="space-y-2">
          <div className="flex items-center justify-between px-1">
            <h2 className="text-xs font-mono font-semibold uppercase tracking-wider text-zinc-400 flex items-center space-x-2">
              <Terminal className="w-3.5 h-3.5 text-indigo-400" />
              <span>Codebase Query Prompt</span>
            </h2>
          </div>
          <QueryInput
            onSubmit={handleQuerySubmit}
            isLoading={isLoadingQuery}
            history={queryHistory}
            onSelectHistory={(q) => handleQuerySubmit(q, 5)}
          />
        </section>

        {/* Answer View & Sources Section */}
        {queryResponse ? (
          <section className="space-y-6 animate-in fade-in duration-300">
            <AnswerView response={queryResponse} />
            <SourceDrawer sources={queryResponse.sources} />
          </section>
        ) : !isLoadingQuery && !queryError ? (
          /* Welcome Empty State */
          <div className="p-8 rounded-2xl border border-zinc-900 bg-zinc-900/30 text-center space-y-6 my-8">
            <div className="inline-flex p-3 rounded-2xl bg-indigo-950/50 border border-indigo-500/20 text-indigo-400">
              <Sparkles className="w-8 h-8" />
            </div>

            <div className="max-w-md mx-auto space-y-2">
              <h3 className="text-base font-bold text-zinc-100 font-mono">
                Ask DevMind AI About Your Codebase
              </h3>
              <p className="text-xs text-zinc-400 leading-relaxed">
                DevMind AI uses AST-aware code chunking, BAAI embeddings, hybrid FAISS search, AST CodeGraph call expansion, and Gemini 3.6 Flash for deep codebase reasoning.
              </p>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 max-w-2xl mx-auto pt-2 text-left font-mono text-xs">
              <button
                onClick={() =>
                  handleQuerySubmit("Where is VerificationEngine implemented?", 5)
                }
                className="p-3 rounded-xl border border-zinc-800/80 bg-zinc-900/80 hover:border-indigo-500/40 hover:bg-zinc-900 transition-all text-zinc-300 group"
              >
                <div className="flex items-center space-x-2 text-indigo-400 group-hover:text-indigo-300 font-semibold mb-1">
                  <Code2 className="w-3.5 h-3.5" />
                  <span>Class Definition</span>
                </div>
                <p className="text-[11px] text-zinc-500 line-clamp-2">
                  "Where is VerificationEngine implemented?"
                </p>
              </button>

              <button
                onClick={() =>
                  handleQuerySubmit("Where is Builder Score calculated?", 5)
                }
                className="p-3 rounded-xl border border-zinc-800/80 bg-zinc-900/80 hover:border-indigo-500/40 hover:bg-zinc-900 transition-all text-zinc-300 group"
              >
                <div className="flex items-center space-x-2 text-indigo-400 group-hover:text-indigo-300 font-semibold mb-1">
                  <Cpu className="w-3.5 h-3.5" />
                  <span>Scoring Engine</span>
                </div>
                <p className="text-[11px] text-zinc-500 line-clamp-2">
                  "Where is Builder Score calculated?"
                </p>
              </button>

              <button
                onClick={() =>
                  handleQuerySubmit(
                    "Which API route handles verification submissions?",
                    5
                  )
                }
                className="p-3 rounded-xl border border-zinc-800/80 bg-zinc-900/80 hover:border-indigo-500/40 hover:bg-zinc-900 transition-all text-zinc-300 group"
              >
                <div className="flex items-center space-x-2 text-indigo-400 group-hover:text-indigo-300 font-semibold mb-1">
                  <Layers className="w-3.5 h-3.5" />
                  <span>API Route Handler</span>
                </div>
                <p className="text-[11px] text-zinc-500 line-clamp-2">
                  "Which API route handles verification?"
                </p>
              </button>
            </div>
          </div>
        ) : null}
      </main>

      {/* Index Modal */}
      <IndexModal
        isOpen={isIndexModalOpen}
        onClose={() => setIsIndexModalOpen(false)}
        onSuccess={handleIndexSuccess}
        onAuthRequired={handleAuthRequired}
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
    </div>
  );
}
