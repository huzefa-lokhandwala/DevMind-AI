"use client";

import React, { useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Logo } from "@/components/public/Logo";
import { Loader2, ArrowRight } from "lucide-react";
import { getStoredAuthToken } from "@/lib/api-client";

export default function AuthSuccessPage() {
  const router = useRouter();

  useEffect(() => {
    const token = getStoredAuthToken();
    if (token) {
      router.replace("/app");
    } else {
      router.replace("/login");
    }
  }, [router]);

  return (
    <div className="min-h-screen bg-[#0c0d0e] text-[#e2e2e2] font-sans flex flex-col items-center justify-center p-6 selection:bg-[#3B82F6]/30 selection:text-[#adc6ff]">
      <div className="w-full max-w-sm rounded-2xl bg-[#141618] border border-[#23252a] p-8 text-center space-y-6 shadow-[0_8px_30px_rgba(0,0,0,0.5)] animate-fade-in-up">
        <div className="flex justify-center">
          <Logo size="lg" href="/" />
        </div>

        <div className="space-y-3">
          <div className="flex justify-center">
            <Loader2 className="w-7 h-7 text-[#3B82F6] animate-spin" />
          </div>
          <h1 className="text-base sm:text-lg font-semibold text-[#f3f4f6]">
            Preparing your workspace...
          </h1>
          <p className="text-xs text-[#9ca3af]">
            Connecting to RAG vector indices and restoring active context.
          </p>
        </div>

        <div className="pt-2">
          <Link
            href="/app"
            className="inline-flex items-center gap-1.5 text-xs text-[#adc6ff] hover:text-white font-medium transition-colors"
          >
            <span>Click here if not automatically redirected</span>
            <ArrowRight className="w-3 h-3" />
          </Link>
        </div>
      </div>
    </div>
  );
}
