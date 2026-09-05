"use client";

import { useState, useEffect, useRef } from "react";
import {
  X,
  GitBranch,
  Folder,
  CheckCircle2,
  AlertCircle,
  RefreshCw,
  Info,
  Clock,
  Sparkles,
  Layers,
} from "lucide-react";
import { indexRepository, getIndexingStatus, AuthError } from "@/lib/api-client";
import { IndexRepositoryResponse } from "@/lib/types";

interface IndexModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: (result: IndexRepositoryResponse) => void;
  onAuthRequired: (message: string) => void;
}

type IndexMode = "github" | "local";

const EDUCATIONAL_TIPS = [
  "DevMind creates a local semantic search index so future questions can retrieve the most relevant parts of your codebase.",
  "The free development server intentionally uses conservative memory settings (512 MB RAM), so indexing is slower but safer.",
  "After indexing, you can ask questions about specific files, functions, or codebase architecture.",
  "You can inspect the exact retrieved source code chunks in the Evidence Inspector after each answer.",
  "Deterministic query routing ensures general technical questions don't trigger unnecessary codebase retrieval.",
];

export function IndexModal({
  isOpen,
  onClose,
  onSuccess,
  onAuthRequired,
}: IndexModalProps) {
  const [mode, setMode] = useState<IndexMode>("github");
  const [githubUrl, setGithubUrl] = useState<string>("");
  const [localPath, setLocalPath] = useState<string>("");
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [isQueued, setIsQueued] = useState<boolean>(false);
  const [queuePosition, setQueuePosition] = useState<number>(0);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [result, setResult] = useState<IndexRepositoryResponse | null>(null);
  const [tipIndex, setTipIndex] = useState<number>(0);

  const pollingIntervalRef = useRef<NodeJS.Timeout | null>(null);

  // Rotating tips timer
  useEffect(() => {
    if (!isOpen || (!isLoading && !isQueued)) return;
    const interval = setInterval(() => {
      setTipIndex((prev) => (prev + 1) % EDUCATIONAL_TIPS.length);
    }, 6000);
    return () => clearInterval(interval);
  }, [isOpen, isLoading, isQueued]);

  // Cleanup polling on unmount
  useEffect(() => {
    return () => {
      if (pollingIntervalRef.current) {
        clearInterval(pollingIntervalRef.current);
      }
    };
  }, []);

  if (!isOpen) return null;

  const pollJobStatus = (jobId: string) => {
    if (pollingIntervalRef.current) clearInterval(pollingIntervalRef.current);

    pollingIntervalRef.current = setInterval(async () => {
      try {
        const statusData = await getIndexingStatus(jobId);
        if (statusData.status === "QUEUED") {
          setIsQueued(true);
          setQueuePosition(statusData.queue_position);
        } else if (statusData.status === "RUNNING") {
          setIsQueued(false);
          setIsLoading(true);
        } else if (statusData.status === "COMPLETED") {
          if (pollingIntervalRef.current) clearInterval(pollingIntervalRef.current);
          setIsLoading(false);
          setIsQueued(false);
          const finalRes = statusData.result || {
            repository: statusData.repository_source,
            files_loaded: 0,
            chunks_created: 0,
            embeddings_created: 0,
            status: "indexed",
          };
          setResult(finalRes);
          onSuccess(finalRes);
        } else if (statusData.status === "FAILED") {
          if (pollingIntervalRef.current) clearInterval(pollingIntervalRef.current);
          setIsLoading(false);
          setIsQueued(false);
          setErrorMsg(statusData.error || "Repository indexing failed.");
        }
      } catch (err: any) {
        // Silently retry polling unless explicit auth error
        if (err instanceof AuthError) {
          if (pollingIntervalRef.current) clearInterval(pollingIntervalRef.current);
          setIsLoading(false);
          setIsQueued(false);
          onAuthRequired(err.message);
          onClose();
        }
      }
    }, 1500);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (isLoading || isQueued) return;

    setErrorMsg(null);
    setResult(null);

    const payload: { github_url?: string; repository_path?: string } = {};

    if (mode === "github") {
      if (!githubUrl.trim()) {
        setErrorMsg("Please enter a valid GitHub repository HTTPS URL.");
        return;
      }
      payload.github_url = githubUrl.trim();
    } else {
      if (!localPath.trim()) {
        setErrorMsg("Please enter a local repository folder path.");
        return;
      }
      payload.repository_path = localPath.trim();
    }

    setIsLoading(true);

    try {
      const res = await indexRepository(payload);
      if (res.status === "queued" && res.job_id) {
        setIsQueued(true);
        setQueuePosition(res.queue_position || 1);
        pollJobStatus(res.job_id);
      } else {
        setIsLoading(false);
        setResult(res);
        onSuccess(res);
      }
    } catch (err: any) {
      setIsLoading(false);
      setIsQueued(false);
      if (err instanceof AuthError) {
        onAuthRequired(err.message);
        onClose();
        return;
      }
      setErrorMsg(err.message || "Failed to index repository.");
    }
  };

  const handleClose = () => {
    if (!isLoading && !isQueued) {
      if (pollingIntervalRef.current) clearInterval(pollingIntervalRef.current);
      setErrorMsg(null);
      setResult(null);
      onClose();
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-[#111111]/80 backdrop-blur-[2px] animate-fade-in-up font-sans">
      <div className="w-full max-w-[500px] bg-[#1C1C1C] border border-[#2A2A2A] rounded-lg overflow-hidden flex flex-col shadow-[0_4px_16px_rgba(0,0,0,0.6)]">
        {/* Header */}
        <div className="p-4 border-b border-[#2A2A2A] flex justify-between items-center bg-[#171717]">
          <div>
            <h2 className="text-base font-semibold text-[#e2e2e2]">
              {isQueued
                ? "Indexing Queued"
                : isLoading
                ? "Indexing in Progress"
                : "Index Repository"}
            </h2>
            <p className="text-xs text-[#8c909f] mt-0.5">
              {isQueued
                ? "Waiting for active indexing job to finish"
                : isLoading
                ? "Building local FAISS semantic search index"
                : "Prepare codebase for semantic retrieval and Q&A"}
            </p>
          </div>
          <button
            onClick={handleClose}
            disabled={isLoading || isQueued}
            className="text-[#8c909f] hover:text-[#e2e2e2] p-1 rounded transition-colors disabled:opacity-30 cursor-pointer"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Indeterminate Animated Progress Bar when active */}
        {(isLoading || isQueued) && (
          <div className="h-[2px] w-full bg-[#2A2A2A] overflow-hidden relative">
            <div className="h-full bg-[#3B82F6] absolute w-1/3 animate-pulse left-1/3"></div>
          </div>
        )}

        {/* Body */}
        <div className="p-5 flex flex-col gap-4">
          {!isLoading && !isQueued && !result && (
            <>
              {/* Segmented Control */}
              <div className="flex bg-[#121414] border border-[#2A2A2A] rounded p-[2px] w-full text-xs font-medium">
                <button
                  type="button"
                  onClick={() => setMode("github")}
                  className={`flex-1 py-1.5 px-3 rounded flex items-center justify-center gap-1.5 transition-all cursor-pointer ${
                    mode === "github"
                      ? "bg-[#282a2b] text-[#e2e2e2] font-semibold border border-[#424754] shadow-sm"
                      : "text-[#8c909f] hover:text-[#e2e2e2]"
                  }`}
                >
                  <GitBranch className="w-3.5 h-3.5" />
                  <span>GitHub Repository</span>
                </button>
                <button
                  type="button"
                  onClick={() => setMode("local")}
                  className={`flex-1 py-1.5 px-3 rounded flex items-center justify-center gap-1.5 transition-all cursor-pointer ${
                    mode === "local"
                      ? "bg-[#282a2b] text-[#e2e2e2] font-semibold border border-[#424754] shadow-sm"
                      : "text-[#8c909f] hover:text-[#e2e2e2]"
                  }`}
                >
                  <Folder className="w-3.5 h-3.5" />
                  <span>Local Path</span>
                </button>
              </div>

              {/* Form Input */}
              <form onSubmit={handleSubmit} className="flex flex-col gap-3">
                <div className="flex flex-col gap-1.5">
                  <label className="text-xs font-medium text-[#e2e2e2]">
                    {mode === "github" ? "GitHub HTTPS URL" : "Local Repository Folder Path"}
                  </label>
                  <input
                    type={mode === "github" ? "url" : "text"}
                    value={mode === "github" ? githubUrl : localPath}
                    onChange={(e) =>
                      mode === "github" ? setGithubUrl(e.target.value) : setLocalPath(e.target.value)
                    }
                    placeholder={
                      mode === "github"
                        ? "https://github.com/huzefa-lokhandwala/proofos"
                        : "repositories/sample_project"
                    }
                    className="w-full bg-[#111111] border border-[#2A2A2A] text-[#e2e2e2] text-xs px-3 py-2 rounded focus:outline-none focus:border-[#3B82F6] focus:ring-1 focus:ring-[#3B82F6] placeholder-[#8c909f]/50 transition-colors font-mono"
                  />
                  <span className="text-[11px] text-[#8c909f]">
                    {mode === "github"
                      ? "Clones shallow depth securely and parses AST symbols."
                      : "Resolves supported source files (.py, .ts, .tsx, .js, .json, etc.)."}
                  </span>
                </div>

                {errorMsg && (
                  <div className="p-3 rounded bg-[#93000a]/20 border border-[#ffb4ab]/30 flex items-start gap-2 text-xs text-[#ffb4ab]">
                    <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
                    <span>{errorMsg}</span>
                  </div>
                )}

                {/* Footer Buttons */}
                <div className="flex items-center justify-end gap-2 pt-2 border-t border-[#2A2A2A] mt-2">
                  <button
                    type="button"
                    onClick={handleClose}
                    className="px-3 py-1.5 text-xs text-[#8c909f] hover:text-[#e2e2e2] rounded transition-colors cursor-pointer"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    className="px-4 py-1.5 text-xs font-medium bg-[#3B82F6] hover:bg-[#2563eb] text-[#F5F5F5] rounded transition-colors cursor-pointer"
                  >
                    Index Repository
                  </button>
                </div>
              </form>
            </>
          )}

          {/* Queued State UI */}
          {isQueued && (
            <div className="flex flex-col gap-3 py-2 animate-fade-in-up">
              <div className="p-3.5 rounded-lg bg-[#304671]/30 border border-[#3B82F6]/40 flex items-start gap-3">
                <Clock className="w-5 h-5 text-[#adc6ff] shrink-0 mt-0.5 animate-pulse" />
                <div className="flex flex-col gap-1 text-xs">
                  <span className="font-semibold text-[#adc6ff]">
                    Another repository is currently indexing
                  </span>
                  <p className="text-[#a1a1aa] leading-relaxed">
                    To prevent memory exhaustion on the 512 MB server, jobs run serialized.
                    Your request is in the queue.
                  </p>
                  <div className="mt-1 font-mono text-xs text-[#e2e2e2]">
                    Queue Position: <span className="text-[#3B82F6] font-bold">{queuePosition}</span>
                  </div>
                </div>
              </div>

              {/* Informative Micro-Tip */}
              <div className="p-3 rounded bg-[#171717] border border-[#2A2A2A] flex items-start gap-2.5 text-xs text-[#8c909f]">
                <Info className="w-4 h-4 text-[#3B82F6] shrink-0 mt-0.5" />
                <p className="italic">{EDUCATIONAL_TIPS[tipIndex]}</p>
              </div>
            </div>
          )}

          {/* Running / Indeterminate Loading UI */}
          {isLoading && !isQueued && (
            <div className="flex flex-col gap-4 py-2">
              <div className="flex items-center gap-3 p-3.5 rounded bg-[#171717] border border-[#2A2A2A]">
                <RefreshCw className="w-5 h-5 text-[#3B82F6] animate-spin shrink-0" />
                <div className="flex flex-col">
                  <span className="text-xs font-medium text-[#e2e2e2]">
                    Building searchable semantic index...
                  </span>
                  <span className="text-[11px] text-[#8c909f] mt-0.5">
                    This can take 1-3 minutes on the free server. Please do not refresh.
                  </span>
                </div>
              </div>

              {/* Helpful Educational Tips Section */}
              <div className="p-3 rounded bg-[#121414] border border-[#2A2A2A] flex items-start gap-2.5 text-xs">
                <Sparkles className="w-4 h-4 text-[#adc6ff] shrink-0 mt-0.5" />
                <div>
                  <span className="text-[10px] uppercase font-mono font-semibold text-[#8c909f] block mb-0.5">
                    Why does this take time?
                  </span>
                  <p className="text-[#a1a1aa] text-xs leading-relaxed transition-all duration-300">
                    {EDUCATIONAL_TIPS[tipIndex]}
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* Success Result View */}
          {result && (
            <div className="flex flex-col gap-4 animate-fade-in-up">
              <div className="p-3.5 rounded bg-[#10B981]/10 border border-[#10B981]/30 flex items-center gap-2.5 text-xs text-[#10B981] font-mono">
                <CheckCircle2 className="w-4 h-4 shrink-0" />
                <span className="font-semibold">Repository '{result.repository}' successfully indexed!</span>
              </div>

              <div className="grid grid-cols-3 gap-2 text-center text-xs font-mono">
                <div className="p-2.5 rounded bg-[#171717] border border-[#2A2A2A]">
                  <div className="text-[10px] text-[#8c909f] uppercase tracking-wider">Files</div>
                  <div className="text-base font-bold text-[#e2e2e2] mt-0.5">{result.files_loaded}</div>
                </div>
                <div className="p-2.5 rounded bg-[#171717] border border-[#2A2A2A]">
                  <div className="text-[10px] text-[#8c909f] uppercase tracking-wider">Chunks</div>
                  <div className="text-base font-bold text-[#e2e2e2] mt-0.5">{result.chunks_created}</div>
                </div>
                <div className="p-2.5 rounded bg-[#171717] border border-[#2A2A2A]">
                  <div className="text-[10px] text-[#8c909f] uppercase tracking-wider">Embeddings</div>
                  <div className="text-base font-bold text-[#adc6ff] mt-0.5">{result.embeddings_created}</div>
                </div>
              </div>

              <div className="flex justify-end pt-2">
                <button
                  type="button"
                  onClick={handleClose}
                  className="px-4 py-1.5 text-xs font-medium bg-[#3B82F6] hover:bg-[#2563eb] text-[#F5F5F5] rounded transition-colors cursor-pointer"
                >
                  Start Querying
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
