"use client";

import React from "react";
import Link from "next/link";
import { Logo } from "./Logo";

export function PublicFooter() {
  return (
    <footer className="w-full border-t border-[#23252a] bg-[#0c0d0e] text-[#9ca3af] font-sans">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12 lg:py-16">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-8 lg:gap-12">
          {/* Brand Col */}
          <div className="space-y-4 md:col-span-1">
            <Logo size="md" href="/" />
            <p className="text-xs text-[#9ca3af] leading-relaxed max-w-xs">
              AI-powered codebase intelligence that connects to your repository, retrieves relevant code, and explains software architecture with grounded answers.
            </p>
            <p className="text-[11px] text-[#6b7280] font-mono">
              Powered by modern AI models and a custom code-intelligence pipeline.
            </p>
          </div>

          {/* Product Links */}
          <div className="space-y-3">
            <h3 className="text-xs font-semibold text-[#f3f4f6] uppercase tracking-wider font-mono">
              Product
            </h3>
            <ul className="space-y-2 text-xs">
              <li>
                <a href="#product" className="hover:text-white transition-colors">
                  Overview
                </a>
              </li>
              <li>
                <a href="#how-it-works" className="hover:text-white transition-colors">
                  How It Works
                </a>
              </li>
              <li>
                <a href="#capabilities" className="hover:text-white transition-colors">
                  Capabilities
                </a>
              </li>
              <li>
                <Link href="/app" className="hover:text-white transition-colors">
                  Workspace
                </Link>
              </li>
            </ul>
          </div>

          {/* Technology Links */}
          <div className="space-y-3">
            <h3 className="text-xs font-semibold text-[#f3f4f6] uppercase tracking-wider font-mono">
              Technology
            </h3>
            <ul className="space-y-2 text-xs">
              <li>
                <a href="#technology" className="hover:text-white transition-colors">
                  Code-Aware RAG
                </a>
              </li>
              <li>
                <a href="#technology" className="hover:text-white transition-colors">
                  AST Chunking
                </a>
              </li>
              <li>
                <a href="#technology" className="hover:text-white transition-colors">
                  FAISS & pgvector
                </a>
              </li>
              <li>
                <a href="#technology" className="hover:text-white transition-colors">
                  Gemini Embedding 2
                </a>
              </li>
            </ul>
          </div>

          {/* Legal / Resources */}
          <div className="space-y-3">
            <h3 className="text-xs font-semibold text-[#f3f4f6] uppercase tracking-wider font-mono">
              Resources
            </h3>
            <ul className="space-y-2 text-xs">
              <li>
                <a
                  href="https://github.com"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="hover:text-white transition-colors"
                >
                  GitHub Repository
                </a>
              </li>
              <li>
                <Link href="/login" className="hover:text-white transition-colors">
                  Sign In
                </Link>
              </li>
              <li>
                <a href="#privacy" className="hover:text-white transition-colors">
                  Privacy Policy
                </a>
              </li>
              <li>
                <a href="#terms" className="hover:text-white transition-colors">
                  Terms of Service
                </a>
              </li>
            </ul>
          </div>
        </div>

        <div className="mt-12 pt-8 border-t border-[#23252a] flex flex-col sm:flex-row items-center justify-between text-xs text-[#6b7280] gap-4">
          <p>© {new Date().getFullYear()} DevMind AI. All rights reserved.</p>
          <p className="font-mono text-[11px] text-[#6b7280]">
            Understand your codebase. Ask anything.
          </p>
        </div>
      </div>
    </footer>
  );
}
