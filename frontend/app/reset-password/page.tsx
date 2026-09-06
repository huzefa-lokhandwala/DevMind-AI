"use client";

import React, { useState } from "react";
import Link from "next/link";
import { Logo } from "@/components/public/Logo";
import { Button } from "@/components/ui/Button";
import { PasswordInput } from "@/components/ui/PasswordInput";
import { PasswordStrength } from "@/components/ui/PasswordStrength";
import { CheckCircle2, ArrowRight } from "lucide-react";

export default function ResetPasswordPage() {
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [passwordError, setPasswordError] = useState("");
  const [confirmPasswordError, setConfirmPasswordError] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [isSuccess, setIsSuccess] = useState(false);

  const [infoMessage, setInfoMessage] = useState<string | null>(null);

  const validate = () => {
    let valid = true;
    setPasswordError("");
    setConfirmPasswordError("");

    if (!password) {
      setPasswordError("Please enter a new password.");
      valid = false;
    } else if (password.length < 8) {
      setPasswordError("Password must be at least 8 characters long.");
      valid = false;
    }

    if (!confirmPassword) {
      setConfirmPasswordError("Please confirm your new password.");
      valid = false;
    } else if (password !== confirmPassword) {
      setConfirmPasswordError("Passwords do not match.");
      valid = false;
    }

    return valid;
  };

  const handleReset = (e: React.FormEvent) => {
    e.preventDefault();
    if (!validate()) return;

    setIsLoading(true);

    // Backend does not currently support reset token verification or password resets.
    setTimeout(() => {
      setIsLoading(false);
      setInfoMessage("Backend password reset service is not yet configured. Please contact your administrator or sign in with your current password.");
    }, 400);
  };

  return (
    <div className="min-h-screen bg-[#0c0d0e] text-[#e2e2e2] font-sans flex flex-col justify-between selection:bg-[#3B82F6]/30 selection:text-[#adc6ff]">
      {/* Top Bar */}
      <div className="p-4 sm:p-6 flex items-center justify-between border-b border-[#1c1e22]">
        <Logo size="md" href="/" />
        <Link
          href="/login"
          className="text-xs text-[#adc6ff] hover:underline font-medium"
        >
          Sign in
        </Link>
      </div>

      {/* Main Container */}
      <div className="flex-1 flex items-center justify-center p-4 sm:p-8">
        <div className="w-full max-w-[420px] rounded-2xl bg-[#141618] border border-[#23252a] p-6 sm:p-8 shadow-[0_8px_30px_rgba(0,0,0,0.5)] space-y-6">
          {/* UI-only Notice Badge */}
          <div className="rounded-lg bg-[#241f17] border border-[#d97706]/40 px-3 py-2 text-xs text-[#fbbf24] flex items-center gap-2">
            <span className="w-1.5 h-1.5 rounded-full bg-[#f59e0b] shrink-0 animate-pulse" />
            <span>UI Preview: Backend password reset endpoint is pending.</span>
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
              Create a new password
            </h1>
            <p className="text-xs sm:text-sm text-[#9ca3af]">
              Enter a new password for your DevMind AI account once configured.
            </p>
          </div>

              <form onSubmit={handleReset} className="space-y-4" noValidate>
                <div className="space-y-1">
                  <label
                    htmlFor="reset-password-new"
                    className="text-xs font-medium text-[#d1d5db]"
                  >
                    New password
                  </label>
                  <PasswordInput
                    id="reset-password-new"
                    placeholder="At least 8 characters"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    error={passwordError}
                    autoComplete="new-password"
                    disabled={isLoading}
                  />
                  <PasswordStrength password={password} />
                </div>

                <div className="space-y-1">
                  <label
                    htmlFor="reset-password-confirm"
                    className="text-xs font-medium text-[#d1d5db]"
                  >
                    Confirm new password
                  </label>
                  <PasswordInput
                    id="reset-password-confirm"
                    placeholder="Re-enter your new password"
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    error={confirmPasswordError}
                    autoComplete="new-password"
                    disabled={isLoading}
                  />
                </div>

                <Button
                  type="submit"
                  variant="primary"
                  fullWidth
                  size="md"
                  isLoading={isLoading}
                  className="mt-2"
                >
                  Update password
                </Button>
              </form>
        </div>
      </div>

      <div className="p-4 text-center text-xs text-[#6b7280] border-t border-[#1c1e22]">
        DevMind AI • AI Codebase Intelligence
      </div>
    </div>
  );
}
