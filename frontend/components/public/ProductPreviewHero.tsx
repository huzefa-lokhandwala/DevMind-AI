"use client";

import React, { useState, useEffect } from "react";
import {
  Terminal,
  FolderGit2,
  MessageSquare,
  FileCode2,
  Search,
  CheckCircle2,
  Copy,
  Check,
  Cpu,
  Layers,
  Sparkles,
  ArrowRight,
  ShieldCheck,
} from "lucide-react";

interface Scenario {
  id: string;
  label: string;
  repository: string;
  filesIndexed: number;
  chunksIndexed: number;
  dimension: string;
  question: string;
  intent: "REPOSITORY" | "GENERAL" | "MIXED";
  latencyMs: number;
  explanation: string;
  sources: {
    file: string;
    filePath: string;
    symbol: string;
    lineRange: string;
    score: number;
    code: string;
  }[];
}

const SCENARIOS: Scenario[] = [
  {
    id: "auth",
    label: "Authentication Flow",
    repository: "devmind-ai",
    filesIndexed: 38,
    chunksIndexed: 412,
    dimension: "768d pgvector",
    question: "How does authentication work in this repository?",
    intent: "REPOSITORY",
    latencyMs: 38.4,
    explanation:
      "Authentication uses Argon2id password hashing and signed HS256 JWT access tokens. Requests submit credentials via POST /auth/login. Protected endpoints inject `get_current_user`, which validates the Bearer token and verifies active account state in PostgreSQL before granting access.",
    sources: [
      {
        file: "app/api/auth.py",
        filePath: "app/api/auth.py",
        symbol: "get_current_user",
        lineRange: "Lines 75–118",
        score: 0.94,
        code: `async def get_current_user(\n    token: str = Depends(oauth2_scheme),\n    db: Session = Depends(get_db),\n) -> UserModel:\n    """Fail-closed dependency validating JWT access token in production."""\n    payload = decode_access_token(token)\n    user_id = int(payload["sub"])\n    user = crud.get_user_by_id(db, user_id=user_id)\n    if not user or not user.is_active:\n        raise HTTPException(status_code=401, detail="Invalid token or inactive user")\n    return user`,
      },
      {
        file: "app/utils/security.py",
        filePath: "app/utils/security.py",
        symbol: "hash_password",
        lineRange: "Lines 23–48",
        score: 0.88,
        code: `_ph = PasswordHasher(time_cost=2, memory_cost=65536, parallelism=1, hash_len=32)\n\ndef hash_password(password: str) -> str:\n    """Hash a plaintext password using Argon2id with OWASP parameters."""\n    if not password or len(password) < 8:\n        raise ValueError("Password must be at least 8 characters long.")\n    return _ph.hash(password)`,
      },
    ],
  },
  {
    id: "database",
    label: "pgvector Storage",
    repository: "devmind-ai",
    filesIndexed: 38,
    chunksIndexed: 412,
    dimension: "768d pgvector",
    question: "Where is the vector database connection configured?",
    intent: "REPOSITORY",
    latencyMs: 29.8,
    explanation:
      "Database models and connections are configured in `app/db/database.py` and `app/db/models.py`. Embeddings are stored as 768-dimensional vectors using pgvector's `Vector(768)` type with cosine distance index querying.",
    sources: [
      {
        file: "app/db/models.py",
        filePath: "app/db/models.py",
        symbol: "ChunkModel",
        lineRange: "Lines 85–112",
        score: 0.92,
        code: `class ChunkModel(Base):\n    __tablename__ = "chunks"\n    id: Mapped[int] = mapped_column(primary_key=True)\n    file_id: Mapped[int] = mapped_column(ForeignKey("files.id", ondelete="CASCADE"))\n    content: Mapped[str] = mapped_column(Text, nullable=False)\n    # Native pgvector 768d column for Gemini Embedding 2\n    embedding: Mapped[list[float]] = mapped_column(Vector(768), nullable=True)`,
      },
      {
        file: "app/db/database.py",
        filePath: "app/db/database.py",
        symbol: "create_engine",
        lineRange: "Lines 20–42",
        score: 0.85,
        code: `DATABASE_URL = os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL)\nif DATABASE_URL.startswith("postgresql://"):\n    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg://", 1)\n\nengine = create_engine(DATABASE_URL, pool_pre_ping=True, echo=False)\nSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)`,
      },
    ],
  },
  {
    id: "retrieval",
    label: "RAG Retrieval Pipeline",
    repository: "devmind-ai",
    filesIndexed: 38,
    chunksIndexed: 412,
    dimension: "768d pgvector",
    question: "Trace the RAG retrieval pipeline from query to response.",
    intent: "REPOSITORY",
    latencyMs: 44.1,
    explanation:
      "The query endpoint passes natural language input into `RAGService.query()`. The query is classified for intent, embedded into a 768d vector via Gemini Embedding 2, and searched against repository-scoped chunks in PostgreSQL via pgvector cosine distance. Retrieved chunks are assembled into a grounded prompt context for LLM generation.",
    sources: [
      {
        file: "app/services/rag_service.py",
        filePath: "app/services/rag_service.py",
        symbol: "RAGService.query",
        lineRange: "Lines 520–585",
        score: 0.96,
        code: `def query(self, query_text: str, repository_name: str, top_k: int = 5):\n    # 1. Authoritative repository ownership check\n    repo = get_repository_by_name(db, repository_name, user_id=user_id)\n    if not repo:\n        raise RepositoryNotFoundError(f"Repository '{repository_name}' not found.")\n    # 2. pgvector scoped retrieval\n    results = self.retriever.retrieve(query_text, k=top_k, repository_id=repo.id)\n    # 3. Context assembly & LLM generation\n    prompt_context = self.context_assembler.assemble(query_text, results)\n    return self.llm_provider.generate(prompt_context)`,
      },
    ],
  },
];

export function ProductPreviewHero() {
  const [activeScenarioIdx, setActiveScenarioIdx] = useState<number>(0);
  const [activeSourceIdx, setActiveSourceIdx] = useState<number>(0);
  const [copiedCode, setCopiedCode] = useState<boolean>(false);
  const [isSimulatingSearch, setIsSimulatingSearch] = useState<boolean>(false);

  const scenario = SCENARIOS[activeScenarioIdx];
  const activeSource = scenario.sources[activeSourceIdx] || scenario.sources[0];

  const handleScenarioChange = (idx: number) => {
    setIsSimulatingSearch(true);
    setActiveScenarioIdx(idx);
    setActiveSourceIdx(0);
    setTimeout(() => {
      setIsSimulatingSearch(false);
    }, 280);
  };

  const handleCopyCode = () => {
    if (!activeSource?.code) return;
    navigator.clipboard.writeText(activeSource.code);
    setCopiedCode(true);
    setTimeout(() => setCopiedCode(false), 2000);
  };

  return (
    <div className="w-full rounded-xl sm:rounded-2xl border border-[#232832] bg-[#0c0e12] shadow-[0_24px_64px_rgba(0,0,0,0.7)] overflow-hidden text-left font-sans text-xs sm:text-sm">
      {/* Top Application Bar */}
      <div className="h-10 px-4 border-b border-[#1c2028] bg-[#101318] flex items-center justify-between select-none">
        <div className="flex items-center gap-2">
          <div className="flex items-center gap-1.5">
            <div className="w-2.5 h-2.5 rounded-full bg-[#ef4444]/80" />
            <div className="w-2.5 h-2.5 rounded-full bg-[#f59e0b]/80" />
            <div className="w-2.5 h-2.5 rounded-full bg-[#10b981]/80" />
          </div>
          <span className="ml-2 font-mono text-[11px] text-[#6b7280]">
            devmind-workspace — {scenario.repository} ({scenario.dimension})
          </span>
        </div>

        <div className="flex items-center gap-2 font-mono text-[11px]">
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-[#10b981]/10 text-[#34d399] border border-[#10b981]/20">
            <span className="w-1.5 h-1.5 rounded-full bg-[#10b981] animate-pulse" />
            <span>Indexed</span>
          </span>
          <span className="text-[#6b7280] hidden sm:inline">
            {scenario.filesIndexed} files · {scenario.chunksIndexed} chunks
          </span>
        </div>
      </div>

      {/* Main Workspace Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-12 min-h-[460px] w-full min-w-0 overflow-hidden">
        {/* Left Side: Repositories & Real Scenario Selector */}
        <div className="lg:col-span-4 border-b lg:border-b-0 lg:border-r border-[#1c2028] bg-[#0e1115] p-3.5 flex flex-col justify-between gap-3 min-w-0">
          <div className="space-y-3 min-w-0">
            {/* Active Repository Card */}
            <div className="p-2.5 rounded-lg bg-[#14171d] border border-[#1f242d] space-y-1 min-w-0">
              <div className="flex items-center justify-between text-[10px] font-mono text-[#6b7280] uppercase tracking-wider">
                <span>Active Repository</span>
                <span className="text-[#3b82f6]">pgvector</span>
              </div>
              <div className="flex items-center gap-2 text-xs font-semibold text-[#f3f4f6] min-w-0">
                <FolderGit2 className="w-4 h-4 text-[#3b82f6] shrink-0" />
                <span className="font-mono truncate">{scenario.repository}</span>
              </div>
            </div>

            {/* Realistic Scenario Prompts */}
            <div className="space-y-1 min-w-0">
              <span className="text-[10px] font-mono text-[#6b7280] uppercase tracking-wider px-2 block mb-1">
                Sample Codebase Queries
              </span>
              {SCENARIOS.map((item, idx) => {
                const isSelected = idx === activeScenarioIdx;
                return (
                  <button
                    key={item.id}
                    type="button"
                    onClick={() => handleScenarioChange(idx)}
                    className={`w-full text-left p-2 rounded-lg text-xs font-medium transition-all cursor-pointer flex items-center justify-between ${
                      isSelected
                        ? "bg-[#182338] text-[#adc6ff] border border-[#3b82f6]/40 shadow-sm"
                        : "text-[#9ca3af] hover:bg-[#14171d] hover:text-[#d1d5db] border border-transparent"
                    }`}
                  >
                    <div className="flex items-center gap-2 min-w-0">
                      <MessageSquare className="w-3.5 h-3.5 shrink-0 opacity-70" />
                      <span className="truncate">{item.label}</span>
                    </div>
                    <ArrowRight className={`w-3 h-3 shrink-0 ${isSelected ? "text-[#3b82f6]" : "opacity-0"}`} />
                  </button>
                );
              })}
            </div>
          </div>

          {/* Technical Diagnostics Badge */}
          <div className="p-2.5 rounded-lg bg-[#12151a] border border-[#1b2027] font-mono text-[11px] text-[#8c909f] space-y-1">
            <div className="flex justify-between">
              <span>Embedding Engine</span>
              <span className="text-[#adc6ff]">Gemini 768d</span>
            </div>
            <div className="flex justify-between">
              <span>Retrieval Isolation</span>
              <span className="text-[#10b981]">Multi-Tenant Safe</span>
            </div>
          </div>
        </div>

        {/* Right Side: Conversation + Evidence Inspector */}
        <div className="lg:col-span-8 p-4 sm:p-5 flex flex-col justify-between bg-[#090b0e] space-y-4 min-w-0 w-full overflow-hidden">
          {/* Messages & Results */}
          <div className="space-y-4 flex-1 min-w-0 w-full">
            {/* User Question */}
            <div className="flex items-start gap-2.5 min-w-0">
              <div className="w-6 h-6 rounded bg-[#1c2028] border border-[#282e3a] flex items-center justify-center text-[#d1d5db] shrink-0 font-mono text-[11px]">
                dev
              </div>
              <div className="p-2.5 sm:p-3 rounded-lg bg-[#12151b] border border-[#1f242e] text-[#f3f4f6] max-w-full min-w-0">
                <p className="font-mono text-xs sm:text-sm font-medium break-words">
                  {scenario.question}
                </p>
              </div>
            </div>

            {/* Assistant Grounded Answer */}
            <div className="flex items-start gap-2.5 min-w-0">
              <div className="w-6 h-6 rounded bg-[#182338] border border-[#3b82f6]/40 flex items-center justify-center text-[#adc6ff] shrink-0">
                <Terminal className="w-3.5 h-3.5 text-[#3b82f6]" />
              </div>

              <div className="space-y-3 flex-1 min-w-0 text-xs sm:text-sm leading-relaxed text-[#d1d5db] overflow-hidden">
                {isSimulatingSearch ? (
                  <div className="py-6 flex items-center gap-2.5 text-[#3b82f6] font-mono text-xs">
                    <span className="w-2 h-2 rounded-full bg-[#3b82f6] animate-ping" />
                    <span>Searching AST chunks and vector index in {scenario.repository}...</span>
                  </div>
                ) : (
                  <>
                    <p className="text-[#e2e8f0] font-sans leading-relaxed">
                      {scenario.explanation}
                    </p>

                    {/* Referenced Evidence Citations */}
                    <div className="pt-3 border-t border-[#1c2028] space-y-2.5 min-w-0">
                      <div className="flex items-center justify-between gap-2 flex-wrap">
                        <div className="flex items-center gap-1.5 font-mono text-[11px] font-semibold text-[#adc6ff] uppercase tracking-wider">
                          <CheckCircle2 className="w-3.5 h-3.5 text-[#10b981] shrink-0" />
                          <span>Grounded Source Evidence ({scenario.sources.length} sources)</span>
                        </div>
                        <span className="text-[10px] font-mono text-[#6b7280]">
                          Latency: {scenario.latencyMs}ms
                        </span>
                      </div>

                      {/* Source File Tabs */}
                      <div className="flex flex-wrap gap-1.5 min-w-0">
                        {scenario.sources.map((src, idx) => {
                          const isSelected = idx === activeSourceIdx;
                          return (
                            <button
                              key={src.file}
                              type="button"
                              onClick={() => setActiveSourceIdx(idx)}
                              className={`px-2.5 py-1 rounded text-[11px] font-mono transition-all cursor-pointer flex items-center gap-1.5 max-w-full truncate ${
                                isSelected
                                  ? "bg-[#182338] text-[#adc6ff] border border-[#3b82f6]/50 shadow-sm"
                                  : "bg-[#12151b] text-[#8c909f] border border-[#1e232c] hover:text-[#d1d5db]"
                              }`}
                            >
                              <FileCode2 className="w-3 h-3 shrink-0" />
                              <span className="truncate">{src.file} ({src.lineRange})</span>
                              <span className="text-[10px] px-1 rounded bg-[#10b981]/15 text-[#34d399] shrink-0">
                                {src.score}
                              </span>
                            </button>
                          );
                        })}
                      </div>

                      {/* Interactive Code Evidence Block */}
                      <div className="rounded-lg border border-[#1f242e] bg-[#07080a] overflow-hidden min-w-0 max-w-full">
                        <div className="h-7 px-3 bg-[#0d0f13] border-b border-[#1c2028] flex items-center justify-between text-[11px] font-mono text-[#8c909f] gap-2">
                          <span className="text-[#9ca3af] truncate">{activeSource.filePath} · {activeSource.symbol}</span>
                          <button
                            type="button"
                            onClick={handleCopyCode}
                            className="flex items-center gap-1 text-[10px] text-[#6b7280] hover:text-[#e2e2e2] transition-colors cursor-pointer shrink-0"
                            title="Copy snippet"
                          >
                            {copiedCode ? <Check className="w-3 h-3 text-[#10b981]" /> : <Copy className="w-3 h-3" />}
                            <span>{copiedCode ? "Copied" : "Copy"}</span>
                          </button>
                        </div>
                        <div className="p-3 font-mono text-[11px] leading-relaxed text-[#c9d1d9] overflow-x-auto max-w-full">
                          <pre className="text-[#adc6ff] overflow-x-auto max-w-full">
                            <code>{activeSource.code}</code>
                          </pre>
                        </div>
                      </div>
                    </div>
                  </>
                )}
              </div>
            </div>
          </div>

          {/* Interactive Composer Footer */}
          <div className="pt-2 border-t border-[#1c2028]">
            <div className="flex items-center gap-2 px-3 py-2 rounded-lg bg-[#111317] border border-[#1f242d] text-[#6b7280]">
              <Search className="w-4 h-4 text-[#6b7280] shrink-0" />
              <span className="text-xs text-[#6b7280] select-none truncate font-mono">
                Ask a technical question about {scenario.repository}...
              </span>
              <div className="ml-auto px-1.5 py-0.5 rounded bg-[#1a1e26] text-[10px] font-mono text-[#9ca3af] hidden sm:block">
                ⌘ + Enter
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
