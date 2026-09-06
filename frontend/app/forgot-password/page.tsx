"use client";

import React, { useState } from "react";
import Link from "next/link";
import { Logo } from "@/components/public/Logo";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Mail, ArrowLeft, CheckCircle2 } from "lucide-react";

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [emailError, setEmailError] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [isSubmitted, setIsSubmitted] = useState(false);

  const [infoMessage, setInfoMessage] = useState<string | null>(null);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setEmailError("");
    setInfoMessage(null);

    if (!email.trim()) {
      setEmailError("Please enter your email address.");
      return;
    }
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      setEmailError("Please enter a valid email address.");
      return;
    }

    setIsLoading(true);

    // Backend does not currently provide a password reset endpoint.
    // Explicitly notify user rather than faking an email delivery.
    setTimeout(() => {
      setIsLoading(false);
      setInfoMessage("Backend password reset service is not yet configured. Please contact your administrator or sign in.");
    }, 400);
  };

  return (
    <div className="min-h-screen bg-[#0c0d0e] text-[#e2e2e2] font-sans flex flex-col justify-between selection:bg-[#3B82F6]/30 selection:text-[#adc6ff]">
      {/* Top Bar */}
      <div className="p-4 sm:p-6 flex items-center justify-between border-b border-[#1c1e22]">
        <Logo size="md" href="/" />
        <Link
          href="/login"
          className="text-xs text-[#adc6ff] hover:underline font-medium flex items-center gap-1"
        >
          <ArrowLeft className="w-3 h-3" />
          <span>Back to login</span>
        </Link>
      </div>

      {/* Main Container */}
      <div className="flex-1 flex items-center justify-center p-4 sm:p-8">
        <div className="w-full max-w-[420px] rounded-2xl bg-[#141618] border border-[#23252a] p-6 sm:p-8 shadow-[0_8px_30px_rgba(0,0,0,0.5)] space-y-6">
          {/* UI-only Notice Badge */}
          <div className="rounded-lg bg-[#241f17] border border-[#d97706]/40 px-3 py-2 text-xs text-[#fbbf24] flex items-center gap-2">
            <span className="w-1.5 h-1.5 rounded-full bg-[#f59e0b] shrink-0 animate-pulse" />
            <span>UI Preview: Backend password reset service is pending.</span>
          </div>

          {infoMessage && (
            <div className="rounded-lg bg-[#182338] border border-[#3B82F6]/40 p-3 text-xs text-[#adc6ff] space-y-2">
              <p>{infoMessage}</p>
              <Link href="/login" className="inline-block text-[#3B82F6] hover:underline font-medium">
                Return to sign in &rarr;
              </Link>
            </div>
          )}

          <div className="space-y-1.5">
            <h1 className="text-xl sm:text-2xl font-semibold text-[#f3f4f6] tracking-tight">
              Reset your password
            </h1>
            <p className="text-xs sm:text-sm text-[#9ca3af] leading-relaxed">
              Enter your email to request password reset instructions once configured.
            </p>
          </div>

              <form onSubmit={handleSubmit} className="space-y-4" noValidate>
                <Input
                  label="Email address"
                  type="email"
                  placeholder="you@example.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  error={emailError}
                  leftIcon={<Mail className="w-4 h-4 text-[#6b7280]" />}
                  autoComplete="email"
                  disabled={isLoading}
                />

                <Button
                  type="submit"
                  variant="primary"
                  fullWidth
                  size="md"
                  isLoading={isLoading}
                >
                  Send reset link
                </Button>
              </form>

              <div className="pt-2 text-center">
                <Link
                  href="/login"
                  className="inline-flex items-center gap-1.5 text-xs text-[#9ca3af] hover:text-white transition-colors"
                >
                  <ArrowLeft className="w-3.5 h-3.5" />
                  <span>Back to login</span>
                </Link>
              </div>
        </div>
      </div>

      <div className="p-4 text-center text-xs text-[#6b7280] border-t border-[#1c1e22]">
        DevMind AI • AI Codebase Intelligence
      </div>
    </div>
  );
}
