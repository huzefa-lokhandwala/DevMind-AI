"use client";

import React from "react";
import Link from "next/link";
import { PublicNavbar } from "@/components/public/PublicNavbar";
import { PublicFooter } from "@/components/public/PublicFooter";
import { ProductPreviewHero } from "@/components/public/ProductPreviewHero";
import {
  ProblemSection,
  HowItWorksSection,
  TechnologySection,
  CapabilitiesSection,
  WhoItIsForSection,
  FinalCTASection,
} from "@/components/public/LandingSections";
import { ArrowRight, ChevronRight } from "lucide-react";

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-[#090b0e] text-[#e2e8f0] font-sans selection:bg-[#3b82f6]/30 selection:text-[#adc6ff] flex flex-col overflow-x-hidden">
      {/* Top Public Navigation */}
      <PublicNavbar />

      {/* Main Narrative Flow */}
      <main className="flex-1 flex flex-col">
        {/* HERO SECTION */}
        <section className="pt-16 sm:pt-24 pb-16 px-4 sm:px-6 lg:px-8 max-w-7xl mx-auto w-full text-center relative">
          {/* Subtle Ambient Radial Glow */}
          <div className="absolute top-12 left-1/2 -translate-x-1/2 w-[540px] h-[260px] bg-[#3b82f6]/8 rounded-full blur-[100px] pointer-events-none -z-10" />

          {/* Eyebrow / Label */}
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-[#12151b] border border-[#202530] text-xs font-mono text-[#adc6ff] mb-6 shadow-sm">
            <span className="w-1.5 h-1.5 rounded-full bg-[#3b82f6] animate-pulse" />
            <span className="font-semibold tracking-wider uppercase">AI Codebase Intelligence</span>
          </div>

          {/* Main Headline */}
          <h1 className="text-4xl sm:text-6xl lg:text-7xl font-semibold tracking-tight text-[#f3f4f6] max-w-4xl mx-auto leading-[1.08]">
            Understand your codebase.
          </h1>

          {/* Supporting Copy */}
          <p className="mt-5 text-sm sm:text-lg text-[#9ca3af] max-w-2xl mx-auto leading-relaxed">
            Ask questions about your repository and get answers grounded in the code that actually powers it.
          </p>

          {/* Primary & Secondary CTAs */}
          <div className="mt-8 flex flex-col sm:flex-row items-center justify-center gap-3">
            <Link
              href="/signup"
              className="w-full sm:w-auto h-11 px-6 rounded-lg bg-[#3b82f6] hover:bg-[#2563eb] text-white font-medium text-sm transition-all shadow-sm flex items-center justify-center gap-2 active:scale-[0.98]"
            >
              <span>Start exploring</span>
              <ArrowRight className="w-4 h-4" />
            </Link>

            <a
              href="#how-it-works"
              className="w-full sm:w-auto h-11 px-5 rounded-lg bg-[#12151b] hover:bg-[#1a1e27] text-[#d1d5db] hover:text-white font-medium text-sm border border-[#222733] transition-all flex items-center justify-center gap-1.5"
            >
              <span>See how it works</span>
              <ChevronRight className="w-4 h-4 text-[#6b7280]" />
            </a>
          </div>

          {/* Hero Product Interactive Showcase */}
          <div className="mt-12 sm:mt-16 max-w-5xl mx-auto">
            <ProductPreviewHero />
          </div>
        </section>

        {/* SECTION A: YOUR REPOSITORY HAS CONTEXT */}
        <ProblemSection />

        {/* SECTION B: ASK QUESTIONS IN PLAIN LANGUAGE */}
        <HowItWorksSection />

        {/* SECTION C: ANSWERS GROUNDED IN YOUR CODE */}
        <TechnologySection />

        {/* SECTION D: FROM QUESTION TO EVIDENCE */}
        <CapabilitiesSection />

        {/* SECTION E: BUILT FOR DEVELOPERS */}
        <WhoItIsForSection />

        {/* SECTION F: FINAL CTA */}
        <FinalCTASection />
      </main>

      {/* Footer */}
      <PublicFooter />
    </div>
  );
}
