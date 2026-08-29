"use client";

import { useState } from "react";
import {
  X,
  GitBranch,
  Folder,
  CheckCircle2,
  AlertCircle,
  RefreshCw,
  Layers,
  FileCode,
  Sparkles,
} from "lucide-react";
import { indexRepository, AuthError } from "@/lib/api-client";
import { IndexRepositoryResponse } from "@/lib/types";

interface IndexModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: (result: IndexRepositoryResponse) => void;
  onAuthRequired: (message: string) => void;
}

type IndexMode = "github" | "local";

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
  const [currentStage, setCurrentStage] = useState<number>(0);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [result, setResult] = useState<IndexRepositoryResponse | null>(null);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
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
    setCurrentStage(1);

    // Timers to provide step feedback during backend indexing
    const timer1 = setTimeout(() => setCurrentStage(2), 1200);
    const timer2 = setTimeout(() => setCurrentStage(3), 2800);
    const timer3 = setTimeout(() => setCurrentStage(4), 4500);

    try {
      const res = await indexRepository(payload);
      clearTimeout(timer1);
      clearTimeout(timer2);
      clearTimeout(timer3);
      setCurrentStage(5);
      setIsLoading(false);
      setResult(res);
      onSuccess(res);
    } catch (err: any) {
      clearTimeout(timer1);
      clearTimeout(timer2);
      clearTimeout(timer3);
      setIsLoading(false);
      setCurrentStage(0);
      if (err instanceof AuthError) {
        onAuthRequired(err.message);
        onClose();
        return;
      }
      setErrorMsg(err.message || "Failed to index repository.");
    }
  };

  const handleClose = () => {
    if (!isLoading) {
      setErrorMsg(null);
      setResult(null);
      setCurrentStage(0);
      onClose();
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-[#111111]/80 backdrop-blur-[2px] animate-fade-in-up font-sans">
      <div className="w-full max-w-[480px] bg-[#1C1C1C] border border-[#2A2A2A] rounded-lg overflow-hidden flex flex-col shadow-[0_4px_12px_rgba(0,0,0,0.5)]">
        {/* Header */}
        <div className="p-4 border-b border-[#2A2A2A] flex justify-between items-center bg-[#171717]">
          <div>
            <h2 className="text-base font-semibold text-[#e2e2e2]">
              {isLoading ? "Indexing Repository" : "Index Repository"}
            </h2>
            <p className="text-xs text-[#8c909f] mt-0.5">
              {isLoading
                ? "Processing AST symbols & semantic embeddings"
                : "Load and index codebase into DevMind RAG engine"}
            </p>
          </div>
          <button
            onClick={handleClose}
            disabled={isLoading}
            className="text-[#8c909f] hover:text-[#e2e2e2] p-1 rounded transition-colors disabled:opacity-30 cursor-pointer"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Progress Bar when loading */}
        {isLoading && (
          <div className="h-[2px] w-full bg-[#2A2A2A]">
            <div
              className="h-full bg-[#3B82F6] transition-all duration-500"
              style={{
                width:
                  currentStage === 1
                    ? "25%"
                    : currentStage === 2
                    ? "50%"
                    : currentStage === 3
                    ? "75%"
                    : currentStage >= 4
                    ? "95%"
                    : "10%",
              }}
            ></div>
          </div>
        )}

        {/* Body */}
        <div className="p-5 flex flex-col gap-4">
          {!isLoading && !result && (
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
                      ? "Clones shallow depth (--depth 1) securely."
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

          {/* Indexing In Progress Stages UI (matching Stitch) */}
          {isLoading && (
            <div className="flex flex-col gap-3 py-1">
              <ul className="flex flex-col gap-2.5 text-xs">
                <li className="flex items-center gap-2.5">
                  {currentStage > 1 ? (
                    <CheckCircle2 className="w-4 h-4 text-[#10B981] shrink-0" />
                  ) : (
                    <RefreshCw className="w-4 h-4 text-[#3B82F6] animate-spin shrink-0" />
                  )}
                  <span className={currentStage >= 1 ? "text-[#e2e2e2]" : "text-[#8c909f]"}>
                    Connecting & loading repository source files...
                  </span>
                </li>

                <li className="flex items-center gap-2.5">
                  {currentStage > 2 ? (
                    <CheckCircle2 className="w-4 h-4 text-[#10B981] shrink-0" />
                  ) : currentStage === 2 ? (
                    <RefreshCw className="w-4 h-4 text-[#3B82F6] animate-spin shrink-0" />
                  ) : (
                    <div className="w-4 h-4 rounded-full border border-[#424754] shrink-0"></div>
                  )}
                  <span className={currentStage >= 2 ? "text-[#e2e2e2]" : "text-[#8c909f]"}>
                    Parsing AST functions, classes & dependency graph...
                  </span>
                </li>

                <li className="flex items-center gap-2.5">
                  {currentStage > 3 ? (
                    <CheckCircle2 className="w-4 h-4 text-[#10B981] shrink-0" />
                  ) : currentStage === 3 ? (
                    <RefreshCw className="w-4 h-4 text-[#3B82F6] animate-spin shrink-0" />
                  ) : (
                    <div className="w-4 h-4 rounded-full border border-[#424754] shrink-0"></div>
                  )}
                  <span className={currentStage >= 3 ? "text-[#e2e2e2]" : "text-[#8c909f]"}>
                    Generating 384d FastEmbed vector embeddings...
                  </span>
                </li>

                <li className="flex items-center gap-2.5">
                  {currentStage > 4 ? (
                    <CheckCircle2 className="w-4 h-4 text-[#10B981] shrink-0" />
                  ) : currentStage === 4 ? (
                    <RefreshCw className="w-4 h-4 text-[#3B82F6] animate-spin shrink-0" />
                  ) : (
                    <div className="w-4 h-4 rounded-full border border-[#424754] shrink-0"></div>
                  )}
                  <span className={currentStage >= 4 ? "text-[#e2e2e2]" : "text-[#8c909f]"}>
                    Building FAISS index & persisting pgvector state...
                  </span>
                </li>
              </ul>
            </div>
          )}

          {/* Success Statistics Result View */}
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
