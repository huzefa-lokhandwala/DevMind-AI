"use client";

import React, { useState } from "react";
import Link from "next/link";
import {
  FolderGit2,
  Cpu,
  Search,
  MessageSquare,
  CheckCircle2,
  FileCode2,
  Network,
  Binary,
  Layers,
  ArrowRight,
  GitFork,
  Code2,
  ShieldCheck,
  Zap,
  Terminal,
  Database,
  ExternalLink,
  ChevronRight,
  FileText,
} from "lucide-react";

/* -------------------------------------------------------------------------- */
/* SECTION A: YOUR REPOSITORY HAS CONTEXT                                     */
/* -------------------------------------------------------------------------- */
export function ProblemSection() {
  return (
    <section id="context" className="py-24 border-t border-[#1c2028] bg-[#090b0e] relative">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 space-y-12">
        <div className="max-w-3xl space-y-3">
          <div className="inline-flex items-center gap-2 px-2.5 py-1 rounded bg-[#182338] border border-[#3b82f6]/30 text-[11px] font-mono text-[#adc6ff]">
            <span>SECTION 01</span>
            <span>·</span>
            <span>REPOSITORY MAPPING</span>
          </div>
          <h2 className="text-2xl sm:text-4xl font-semibold text-[#f3f4f6] tracking-tight">
            Your repository has context.
          </h2>
          <p className="text-sm sm:text-base text-[#9ca3af] leading-relaxed">
            Generic chatbots treat code as arbitrary tokens. DevMind analyzes files, AST symbols, function hierarchies, and module boundaries so that every query searches real architectural context.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
          {/* Card 1 */}
          <div className="p-6 rounded-xl bg-[#0f1217] border border-[#1e232d] hover:border-[#3b82f6]/40 transition-all space-y-4">
            <div className="w-9 h-9 rounded-lg bg-[#141820] border border-[#232834] flex items-center justify-center text-[#3b82f6]">
              <FolderGit2 className="w-5 h-5" />
            </div>
            <h3 className="text-base font-semibold text-[#f3f4f6]">Source Code Ingestion</h3>
            <p className="text-xs sm:text-sm text-[#9ca3af] leading-relaxed">
              Walks repository trees while ignoring lockfiles, virtual environments, and binary blobs. Bounded by memory thresholds to run safely on constrained instances.
            </p>
            <div className="pt-2 font-mono text-[11px] text-[#6b7280]">
              Supports .py, .ts, .tsx, .js, .json, .md
            </div>
          </div>

          {/* Card 2 */}
          <div className="p-6 rounded-xl bg-[#0f1217] border border-[#1e232d] hover:border-[#3b82f6]/40 transition-all space-y-4">
            <div className="w-9 h-9 rounded-lg bg-[#141820] border border-[#232834] flex items-center justify-center text-[#3b82f6]">
              <Code2 className="w-5 h-5" />
            </div>
            <h3 className="text-base font-semibold text-[#f3f4f6]">AST-Aware Chunking</h3>
            <p className="text-xs sm:text-sm text-[#9ca3af] leading-relaxed">
              Preserves function definitions, classes, docstrings, and line bounds instead of arbitrary character splitting, ensuring semantic integrity for vector indexing.
            </p>
            <div className="pt-2 font-mono text-[11px] text-[#6b7280]">
              Exact line number attribution
            </div>
          </div>

          {/* Card 3 */}
          <div className="p-6 rounded-xl bg-[#0f1217] border border-[#1e232d] hover:border-[#3b82f6]/40 transition-all space-y-4">
            <div className="w-9 h-9 rounded-lg bg-[#141820] border border-[#232834] flex items-center justify-center text-[#10b981]">
              <Database className="w-5 h-5" />
            </div>
            <h3 className="text-base font-semibold text-[#f3f4f6]">768d Vector Persistence</h3>
            <p className="text-xs sm:text-sm text-[#9ca3af] leading-relaxed">
              Gemini Embedding 2 vectors stored directly in PostgreSQL via pgvector, strictly scoped by repository ownership to guarantee multi-tenant retrieval safety.
            </p>
            <div className="pt-2 font-mono text-[11px] text-[#6b7280]">
              Native cosine distance search
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

/* -------------------------------------------------------------------------- */
/* SECTION B: ASK QUESTIONS IN PLAIN LANGUAGE                                 */
/* -------------------------------------------------------------------------- */
export function HowItWorksSection() {
  const sampleQueries = [
    {
      query: "Where is authentication handled?",
      target: "app/api/auth.py",
      description: "Traces JWT verification dependency and Argon2id hash checks.",
    },
    {
      query: "How does a request reach PostgreSQL?",
      target: "app/db/database.py",
      description: "Explains connection pooling, SQLAlchemy models, and pgvector types.",
    },
    {
      query: "What happens when a repository is indexed?",
      target: "app/services/indexing_coordinator.py",
      description: "Follows atomic lock acquisition, AST parsing, and chunk persistence.",
    },
    {
      query: "Which files are responsible for JWT validation?",
      target: "app/utils/security.py",
      description: "Inspects PyJWT decoding, expiration checks, and signing secret enforcement.",
    },
  ];

  return (
    <section id="how-it-works" className="py-24 border-t border-[#1c2028] bg-[#0c0e12]">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 space-y-12">
        <div className="max-w-3xl space-y-3">
          <div className="inline-flex items-center gap-2 px-2.5 py-1 rounded bg-[#182338] border border-[#3b82f6]/30 text-[11px] font-mono text-[#adc6ff]">
            <span>SECTION 02</span>
            <span>·</span>
            <span>NATURAL LANGUAGE INTERROGATION</span>
          </div>
          <h2 className="text-2xl sm:text-4xl font-semibold text-[#f3f4f6] tracking-tight">
            Ask questions in plain language.
          </h2>
          <p className="text-sm sm:text-base text-[#9ca3af] leading-relaxed">
            Developers spend more time reading unfamiliar code than writing new lines. DevMind translates high-level engineering questions directly into targeted repository retrieval.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {sampleQueries.map((item, idx) => (
            <div
              key={item.query}
              className="p-5 rounded-xl bg-[#111419] border border-[#1e232d] hover:border-[#3b82f6]/40 transition-all flex flex-col justify-between gap-3 group"
            >
              <div className="space-y-2">
                <div className="flex items-center justify-between text-[11px] font-mono">
                  <span className="text-[#3b82f6]">0{idx + 1} · QUESTION</span>
                  <span className="text-[#6b7280]">{item.target}</span>
                </div>
                <h3 className="text-sm sm:text-base font-mono font-medium text-[#f3f4f6] group-hover:text-[#adc6ff] transition-colors">
                  &ldquo;{item.query}&rdquo;
                </h3>
              </div>
              <p className="text-xs text-[#9ca3af] leading-relaxed">
                {item.description}
              </p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

/* -------------------------------------------------------------------------- */
/* SECTION C: ANSWERS GROUNDED IN YOUR CODE                                   */
/* -------------------------------------------------------------------------- */
export function TechnologySection() {
  return (
    <section id="technology" className="py-24 border-t border-[#1c2028] bg-[#090b0e]">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 space-y-12">
        <div className="max-w-3xl space-y-3">
          <div className="inline-flex items-center gap-2 px-2.5 py-1 rounded bg-[#182338] border border-[#3b82f6]/30 text-[11px] font-mono text-[#adc6ff]">
            <span>SECTION 03</span>
            <span>·</span>
            <span>EVIDENCE GROUNDING</span>
          </div>
          <h2 className="text-2xl sm:text-4xl font-semibold text-[#f3f4f6] tracking-tight">
            Answers grounded in your code.
          </h2>
          <p className="text-sm sm:text-base text-[#9ca3af] leading-relaxed">
            Every AI statement links directly to specific source files and line ranges. You never have to wonder if an answer is hallucinated.
          </p>
        </div>

        {/* Side-by-Side Explanation vs Evidence */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 w-full min-w-0">
          {/* Explanation Box */}
          <div className="lg:col-span-6 p-6 rounded-xl bg-[#0f1217] border border-[#1e232d] space-y-4 flex flex-col justify-between min-w-0">
            <div className="space-y-3 min-w-0">
              <div className="flex items-center gap-2 font-mono text-xs text-[#adc6ff]">
                <Terminal className="w-4 h-4 text-[#3b82f6]" />
                <span>Executive Answer</span>
              </div>
              <p className="text-xs sm:text-sm text-[#d1d5db] leading-relaxed font-sans">
                The indexing pipeline guarantees memory safety by utilizing a single-job concurrency lock backed by Redis. Incoming requests receive an observable queue position, while active jobs maintain atomic heartbeat leases renewed every 3.3 seconds.
              </p>
              <div className="p-3 rounded-lg bg-[#141820] border border-[#1e232c] text-xs font-mono text-[#9ca3af] space-y-1">
                <div className="text-[#34d399] flex items-center gap-1.5">
                  <CheckCircle2 className="w-3.5 h-3.5" />
                  <span>2 Source Evidence Chunks Verified</span>
                </div>
                <div className="text-[#6b7280]">pgvector Cosine Distance Match: 0.94</div>
              </div>
            </div>

            <div className="pt-3 border-t border-[#1b1f28] flex items-center justify-between font-mono text-[11px] text-[#6b7280]">
              <span>Latency: 38.4ms</span>
              <span>Provider: Gemini 2.5 Flash</span>
            </div>
          </div>

          {/* Evidence Inspector Box */}
          <div className="lg:col-span-6 p-6 rounded-xl bg-[#0f1217] border border-[#1e232d] space-y-4 min-w-0 max-w-full overflow-hidden">
            <div className="flex items-center justify-between border-b border-[#1b1f28] pb-3 gap-2">
              <div className="flex items-center gap-2 font-mono text-xs text-[#f3f4f6] truncate min-w-0">
                <FileCode2 className="w-4 h-4 text-[#3b82f6] shrink-0" />
                <span className="truncate">app/services/indexing_coordinator.py</span>
              </div>
              <span className="text-[11px] font-mono text-[#adc6ff] px-2 py-0.5 rounded bg-[#182338] shrink-0">
                Lines 109–125
              </span>
            </div>

            <div className="p-3.5 rounded-lg bg-[#07080a] border border-[#1a1e26] font-mono text-[11px] leading-relaxed text-[#adc6ff] overflow-x-auto max-w-full">
              <pre className="overflow-x-auto max-w-full">
                <code>
                  <span className="text-[#5c6370]"># Atomic lock renewal and heartbeat tracking</span>
                  {"\n"}self.lock_ttl_sec = lock_ttl_sec
                  {"\n"}self.renew_interval_sec = max(1.0, float(lock_ttl_sec) / 3.0)
                  {"\n"}self.stale_threshold_sec = max(15.0, self.renew_interval_sec * 3.0)
                  {"\n"}{"\n"}
                  <span className="text-[#c678dd]">if</span> self._redis_url:
                  {"\n"}  self._redis = redis.Redis.from_url(self._redis_url)
                </code>
              </pre>
            </div>

            <p className="text-[11px] text-[#6b7280] font-mono">
              Evidence includes start line, end line, containing symbol, and similarity score.
            </p>
          </div>
        </div>
      </div>
    </section>
  );
}

/* -------------------------------------------------------------------------- */
/* SECTION D: FROM QUESTION TO EVIDENCE (PIPELINE)                            */
/* -------------------------------------------------------------------------- */
export function CapabilitiesSection() {
  const pipelineSteps = [
    {
      step: "01",
      title: "Question Input",
      detail: "Natural language query entered with optional repository scope and top_k parameter.",
    },
    {
      step: "02",
      title: "Repository Retrieval",
      detail: "Query is embedded into 768d space and searched against verified repository chunks.",
    },
    {
      step: "03",
      title: "AST Context Assembly",
      detail: "Code chunks, line ranges, and symbols are assembled into a deterministic prompt context.",
    },
    {
      step: "04",
      title: "Reasoning & Grounding",
      detail: "LLM synthesizes an architectural explanation strictly using retrieved code evidence.",
    },
    {
      step: "05",
      title: "Evidence Inspection",
      detail: "Developer reviews syntax-highlighted code blocks, line numbers, and file paths side-by-side.",
    },
  ];

  return (
    <section id="capabilities" className="py-24 border-t border-[#1c2028] bg-[#0c0e12]">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 space-y-12">
        <div className="max-w-3xl space-y-3">
          <div className="inline-flex items-center gap-2 px-2.5 py-1 rounded bg-[#182338] border border-[#3b82f6]/30 text-[11px] font-mono text-[#adc6ff]">
            <span>SECTION 04</span>
            <span>·</span>
            <span>END-TO-END WORKFLOW</span>
          </div>
          <h2 className="text-2xl sm:text-4xl font-semibold text-[#f3f4f6] tracking-tight">
            From question to evidence.
          </h2>
          <p className="text-sm sm:text-base text-[#9ca3af] leading-relaxed">
            The precise data flow that guarantees reliable, repeatable, and verifiable answers across any codebase.
          </p>
        </div>

        {/* Linear Technical Flow */}
        <div className="grid grid-cols-1 md:grid-cols-5 gap-3">
          {pipelineSteps.map((item) => (
            <div
              key={item.step}
              className="p-5 rounded-xl bg-[#101318] border border-[#1e232d] flex flex-col justify-between gap-4"
            >
              <div className="space-y-2">
                <span className="text-xs font-mono font-semibold text-[#3b82f6]">
                  PHASE {item.step}
                </span>
                <h3 className="text-sm font-semibold text-[#f3f4f6]">{item.title}</h3>
              </div>
              <p className="text-xs text-[#9ca3af] leading-relaxed">
                {item.detail}
              </p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

/* -------------------------------------------------------------------------- */
/* SECTION E: BUILT FOR DEVELOPERS                                            */
/* -------------------------------------------------------------------------- */
export function WhoItIsForSection() {
  return (
    <section id="who-it-is-for" className="py-24 border-t border-[#1c2028] bg-[#090b0e]">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 space-y-12">
        <div className="max-w-3xl space-y-3">
          <div className="inline-flex items-center gap-2 px-2.5 py-1 rounded bg-[#182338] border border-[#3b82f6]/30 text-[11px] font-mono text-[#adc6ff]">
            <span>SECTION 05</span>
            <span>·</span>
            <span>ENGINEERING CREDIBILITY</span>
          </div>
          <h2 className="text-2xl sm:text-4xl font-semibold text-[#f3f4f6] tracking-tight">
            Built for developers.
          </h2>
          <p className="text-sm sm:text-base text-[#9ca3af] leading-relaxed">
            Designed for engineers navigating unfamiliar codebases, verifying pull requests, tracing cross-file dependencies, and onboarding to large production repositories.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
          <div className="p-6 rounded-xl bg-[#0f1217] border border-[#1e232d] space-y-3">
            <h3 className="text-sm font-semibold text-[#f3f4f6]">Multi-Tenant Isolation</h3>
            <p className="text-xs sm:text-sm text-[#9ca3af] leading-relaxed">
              Every indexed repository, conversation, and vector chunk is strictly partitioned by user account. Cross-tenant access attempts return safe 404 responses.
            </p>
          </div>

          <div className="p-6 rounded-xl bg-[#0f1217] border border-[#1e232d] space-y-3">
            <h3 className="text-sm font-semibold text-[#f3f4f6]">Persistent Conversations</h3>
            <p className="text-xs sm:text-sm text-[#9ca3af] leading-relaxed">
              Message history is preserved with repository context in PostgreSQL. Return to past codebase investigations with full evidence citations intact.
            </p>
          </div>

          <div className="p-6 rounded-xl bg-[#0f1217] border border-[#1e232d] space-y-3">
            <h3 className="text-sm font-semibold text-[#f3f4f6]">Multi-Provider Fallback</h3>
            <p className="text-xs sm:text-sm text-[#9ca3af] leading-relaxed">
              Primary generation via Google Gemini with automated failover to OpenRouter and xAI Grok on transient rate limits or upstream service disruptions.
            </p>
          </div>
        </div>
      </div>
    </section>
  );
}

/* -------------------------------------------------------------------------- */
/* SECTION: DEVELOPMENT ARCHITECTURE (PRESERVED EXPORT)                       */
/* -------------------------------------------------------------------------- */
export function DevelopmentStorySection() {
  return null; // Integrated into Built for Developers and Technology sections
}

/* -------------------------------------------------------------------------- */
/* SECTION: DETAILED PRODUCT PREVIEW (PRESERVED EXPORT)                       */
/* -------------------------------------------------------------------------- */
export function DetailedProductPreviewSection() {
  return null; // Integrated cleanly into the interactive ProductPreviewHero
}

/* -------------------------------------------------------------------------- */
/* SECTION F: FINAL CTA                                                       */
/* -------------------------------------------------------------------------- */
export function FinalCTASection() {
  return (
    <section className="py-28 border-t border-[#1c2028] bg-[#090b0e] text-center font-sans">
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 space-y-6">
        <h2 className="text-3xl sm:text-5xl font-semibold text-[#f3f4f6] tracking-tight">
          Understand your codebase.
        </h2>
        <p className="text-sm sm:text-base text-[#9ca3af] max-w-xl mx-auto leading-relaxed">
          Index your repository and interrogate it with grounded, evidence-based AI reasoning.
        </p>

        <div className="pt-4 flex flex-col sm:flex-row items-center justify-center gap-3">
          <Link
            href="/signup"
            className="w-full sm:w-auto h-11 px-6 rounded-lg bg-[#3b82f6] hover:bg-[#2563eb] text-white font-medium text-sm transition-all shadow-sm flex items-center justify-center gap-2 active:scale-[0.98]"
          >
            <span>Start with DevMind</span>
            <ArrowRight className="w-4 h-4" />
          </Link>
          <Link
            href="/login"
            className="w-full sm:w-auto h-11 px-6 rounded-lg bg-[#14171d] hover:bg-[#1a1e26] text-[#f3f4f6] font-medium text-sm border border-[#222733] transition-all flex items-center justify-center"
          >
            Sign In
          </Link>
        </div>
      </div>
    </section>
  );
}
