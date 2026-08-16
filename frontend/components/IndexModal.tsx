"use client";

import { useState } from "react";
import { X, GitBranch, Folder, Loader2, CheckCircle2, AlertCircle, Sparkles } from "lucide-react";
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
  const [statusMessage, setStatusMessage] = useState<string>("");
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
        setErrorMsg("Please enter a valid GitHub repository URL.");
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
    setStatusMessage("Indexing repository...");

    try {
      // Step feedback messages
      const timer1 = setTimeout(() => setStatusMessage("Parsing AST symbols & files..."), 1500);
      const timer2 = setTimeout(() => setStatusMessage("Creating 768d Gemini embeddings & CodeGraph..."), 3500);

      const res = await indexRepository(payload);

      clearTimeout(timer1);
      clearTimeout(timer2);

      setIsLoading(false);
      setResult(res);
      onSuccess(res);
    } catch (err: any) {
      setIsLoading(false);
      if (err instanceof AuthError) {
        onAuthRequired(err.message);
        onClose();
        return;
      }
      setErrorMsg(err.message || "Failed to index repository.");
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="w-full max-w-lg bg-zinc-900 border border-zinc-800 rounded-xl shadow-2xl overflow-hidden font-sans">
        {/* Modal Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-zinc-800 bg-zinc-950/50">
          <div className="flex items-center space-x-2.5">
            <div className="p-2 rounded-lg bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
              <Sparkles className="w-4 h-4" />
            </div>
            <div>
              <h3 className="text-sm font-semibold text-zinc-100 font-mono">Index Codebase Repository</h3>
              <p className="text-xs text-zinc-400">Load AST structure, symbols, and vector embeddings</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-md text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Modal Body */}
        <div className="p-6 space-y-5">
          {/* Mode Switcher Tabs */}
          <div className="grid grid-cols-2 p-1 rounded-lg bg-zinc-950 border border-zinc-800 text-xs font-mono">
            <button
              type="button"
              onClick={() => setMode("github")}
              className={`flex items-center justify-center space-x-2 py-2 rounded-md transition-all ${
                mode === "github"
                  ? "bg-zinc-800 text-indigo-300 font-semibold shadow-sm"
                  : "text-zinc-400 hover:text-zinc-200"
              }`}
            >
              <GitBranch className="w-3.5 h-3.5" />
              <span>GitHub Repository</span>
            </button>
            <button
              type="button"
              onClick={() => setMode("local")}
              className={`flex items-center justify-center space-x-2 py-2 rounded-md transition-all ${
                mode === "local"
                  ? "bg-zinc-800 text-indigo-300 font-semibold shadow-sm"
                  : "text-zinc-400 hover:text-zinc-200"
              }`}
            >
              <Folder className="w-3.5 h-3.5" />
              <span>Local Path</span>
            </button>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            {mode === "github" ? (
              <div className="space-y-1.5">
                <label className="block text-xs font-mono font-medium text-zinc-300">
                  Public GitHub Repository HTTPS URL
                </label>
                <input
                  type="url"
                  value={githubUrl}
                  onChange={(e) => setGithubUrl(e.target.value)}
                  placeholder="https://github.com/username/repository"
                  disabled={isLoading}
                  className="w-full px-3 py-2 rounded-md bg-zinc-950 border border-zinc-800 text-zinc-100 text-sm font-mono placeholder:text-zinc-600 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 disabled:opacity-50 transition-all"
                />
                <p className="text-[11px] text-zinc-500 font-mono">
                  Example: https://github.com/huzefa-lokhandwala/proofos
                </p>
              </div>
            ) : (
              <div className="space-y-1.5">
                <label className="block text-xs font-mono font-medium text-zinc-300">
                  Local Repository Directory Path
                </label>
                <input
                  type="text"
                  value={localPath}
                  onChange={(e) => setLocalPath(e.target.value)}
                  placeholder="repositories/sample_project"
                  disabled={isLoading}
                  className="w-full px-3 py-2 rounded-md bg-zinc-950 border border-zinc-800 text-zinc-100 text-sm font-mono placeholder:text-zinc-600 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 disabled:opacity-50 transition-all"
                />
                <p className="text-[11px] text-zinc-500 font-mono">
                  Example: repositories/sample_project
                </p>
              </div>
            )}

            {/* Error Message Alert */}
            {errorMsg && (
              <div className="p-3 rounded-lg bg-rose-500/10 border border-rose-500/30 flex items-start space-x-2 text-xs text-rose-300 font-mono">
                <AlertCircle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
                <span>{errorMsg}</span>
              </div>
            )}

            {/* Loading Feedback State */}
            {isLoading && (
              <div className="p-4 rounded-lg bg-zinc-950 border border-zinc-800 flex items-center space-x-3 text-xs font-mono text-indigo-300">
                <Loader2 className="w-4 h-4 text-indigo-400 animate-spin shrink-0" />
                <span>{statusMessage}</span>
              </div>
            )}

            {/* Success Result Statistics Card */}
            {result && (
              <div className="p-4 rounded-lg bg-emerald-500/10 border border-emerald-500/30 space-y-2 font-mono">
                <div className="flex items-center space-x-2 text-xs text-emerald-400 font-semibold">
                  <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                  <span>Repository Indexed Successfully</span>
                </div>
                <div className="grid grid-cols-3 gap-2 pt-1 text-center text-xs">
                  <div className="p-2 rounded bg-zinc-900 border border-zinc-800">
                    <div className="text-zinc-400 text-[10px]">Files</div>
                    <div className="font-bold text-zinc-100">{result.files_loaded}</div>
                  </div>
                  <div className="p-2 rounded bg-zinc-900 border border-zinc-800">
                    <div className="text-zinc-400 text-[10px]">Chunks</div>
                    <div className="font-bold text-zinc-100">{result.chunks_created}</div>
                  </div>
                  <div className="p-2 rounded bg-zinc-900 border border-zinc-800">
                    <div className="text-zinc-400 text-[10px]">Embeddings</div>
                    <div className="font-bold text-zinc-100">{result.embeddings_created}</div>
                  </div>
                </div>
              </div>
            )}

            {/* Actions */}
            <div className="flex items-center justify-end space-x-2 pt-2">
              <button
                type="button"
                onClick={onClose}
                disabled={isLoading}
                className="px-4 py-2 rounded-md text-zinc-400 hover:text-zinc-200 text-xs font-mono transition-colors disabled:opacity-50"
              >
                {result ? "Close" : "Cancel"}
              </button>
              {!result && (
                <button
                  type="submit"
                  disabled={isLoading}
                  className="flex items-center space-x-2 px-5 py-2 rounded-md bg-indigo-600 hover:bg-indigo-500 text-white font-mono text-xs font-medium transition-colors shadow-sm disabled:opacity-50"
                >
                  {isLoading ? (
                    <>
                      <Loader2 className="w-3.5 h-3.5 animate-spin" />
                      <span>Indexing...</span>
                    </>
                  ) : (
                    <span>Start Indexing</span>
                  )}
                </button>
              )}
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}
