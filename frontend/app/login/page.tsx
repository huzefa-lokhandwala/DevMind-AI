"use client";

import React, { useState, useRef } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Logo } from "@/components/public/Logo";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { PasswordInput } from "@/components/ui/PasswordInput";
import {
  Mail,
  ArrowRight,
  FolderGit2,
  Terminal,
  ShieldAlert,
  Sparkles,
} from "lucide-react";
import {
  loginUser,
  setStoredAuthToken,
  setStoredUser,
  AuthError,
  ValidationError,
} from "@/lib/api-client";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [emailError, setEmailError] = useState("");
  const [passwordError, setPasswordError] = useState("");
  const [formError, setFormError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const isSubmittingRef = useRef(false);

  const validate = () => {
    let valid = true;
    setEmailError("");
    setPasswordError("");
    setFormError(null);

    if (!email.trim()) {
      setEmailError("Please enter your email address.");
      valid = false;
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      setEmailError("Please enter a valid email address.");
      valid = false;
    }

    if (!password) {
      setPasswordError("Please enter your password.");
      valid = false;
    } else if (password.length < 6) {
      setPasswordError("Password must be at least 6 characters.");
      valid = false;
    }

    return valid;
  };

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    if (isSubmittingRef.current || isLoading) return;
    if (!validate()) return;

    isSubmittingRef.current = true;
    setIsLoading(true);
    setFormError(null);

    try {
      const res = await loginUser({ email: email.trim(), password });
      setStoredAuthToken(res.access_token);
      setStoredUser(res.user);
      router.push("/app");
    } catch (err: any) {
      if (err instanceof AuthError) {
        setFormError("Invalid email or password.");
      } else if (err instanceof ValidationError) {
        setFormError(err.message || "Please check your email and password format.");
      } else if (err.status === 401) {
        setFormError("Invalid email or password.");
      } else {
        setFormError(err.message || "Unable to reach server. Please check your connection and try again.");
      }
    } finally {
      setIsLoading(false);
      isSubmittingRef.current = false;
    }
  };

  return (
    <div className="min-h-screen bg-[#0c0d0e] text-[#e2e2e2] font-sans flex flex-col justify-between selection:bg-[#3B82F6]/30 selection:text-[#adc6ff]">
      {/* Mobile Top Logo */}
      <div className="p-4 sm:p-6 lg:hidden flex items-center justify-between border-b border-[#1c1e22]">
        <Logo size="md" href="/" />
        <Link
          href="/signup"
          className="text-xs text-[#adc6ff] hover:underline font-medium"
        >
          Create account
        </Link>
      </div>

      {/* Main Container */}
      <div className="flex-1 flex items-center justify-center p-4 sm:p-8 lg:p-12">
        <div className="w-full max-w-5xl grid grid-cols-1 lg:grid-cols-12 gap-8 lg:gap-12 items-center">
          {/* LEFT SIDE: Branding & Code Visual */}
          <div className="hidden lg:flex lg:col-span-6 flex-col justify-between space-y-8 pr-4">
            <div className="space-y-4">
              <Logo size="lg" href="/" />
              <div className="space-y-2 pt-4">
                <h1 className="text-3xl sm:text-4xl font-semibold text-[#f3f4f6] tracking-tight leading-tight">
                  Your codebase.
                  <br />
                  <span className="text-[#3B82F6]">Now conversational.</span>
                </h1>
                <p className="text-sm text-[#9ca3af] max-w-md leading-relaxed">
                  Sign in to continue exploring your repositories with DevMind AI.
                </p>
              </div>
            </div>

            {/* Subtle Product/Code Visual */}
            <div className="p-4 rounded-xl bg-[#121417] border border-[#22252c] font-mono text-xs space-y-3 shadow-xl">
              <div className="flex items-center justify-between text-[11px] text-[#6b7280] border-b border-[#22252c] pb-2">
                <div className="flex items-center gap-2">
                  <Terminal className="w-3.5 h-3.5 text-[#3B82F6]" />
                  <span>retrieval_session.py</span>
                </div>
                <span className="text-[#10b981]">768d pgvector</span>
              </div>
              <pre className="text-[#9ca3af] leading-relaxed overflow-x-auto text-[11px]">
                <code>
                  <span className="text-[#6b7280]"># Verify session and context vector space</span>{"\n"}
                  <span className="text-[#c678dd]">async def</span>{" "}
                  <span className="text-[#61afef]">authenticate_workspace</span>(repo_id):{"\n"}
                  {"  "}session = <span className="text-[#c678dd]">await</span> load_context(repo_id){"\n"}
                  {"  "}<span className="text-[#c678dd]">return</span> session.connect_grounded_rag()
                </code>
              </pre>
            </div>

            <p className="text-xs text-[#6b7280]">
              Powered by modern AI models and a custom code-intelligence pipeline.
            </p>
          </div>

          {/* RIGHT SIDE: Authentication Card */}
          <div className="lg:col-span-6 flex justify-center">
            <div className="w-full max-w-[420px] rounded-2xl bg-[#141618] border border-[#23252a] p-6 sm:p-8 shadow-[0_8px_30px_rgba(0,0,0,0.5)] space-y-6">
              {/* Card Header */}
              <div className="space-y-1.5">
                <h2 className="text-xl sm:text-2xl font-semibold text-[#f3f4f6] tracking-tight">
                  Welcome back
                </h2>
                <p className="text-xs sm:text-sm text-[#9ca3af]">
                  Sign in to continue to DevMind AI.
                </p>
              </div>

              {/* Form Level Error Alert */}
              {formError && (
                <div
                  role="alert"
                  className="p-3 rounded-lg bg-[#ef4444]/15 border border-[#ef4444]/30 text-xs text-[#fca5a5] flex items-center gap-2 animate-fade-in-up"
                >
                  <ShieldAlert className="w-4 h-4 shrink-0 text-[#ef4444]" />
                  <span>{formError}</span>
                </div>
              )}

              {/* Login Form */}
              <form onSubmit={handleLogin} className="space-y-4" noValidate>
                <Input
                  id="login-email"
                  name="email"
                  label="Email"
                  type="email"
                  placeholder="you@example.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  error={emailError}
                  leftIcon={<Mail className="w-4 h-4 text-[#6b7280]" />}
                  autoComplete="email"
                  disabled={isLoading}
                />

                <div className="space-y-1">
                  <div className="flex items-center justify-between">
                    <label
                      htmlFor="login-password"
                      className="text-xs font-medium text-[#d1d5db]"
                    >
                      Password
                    </label>
                    <Link
                      href="/forgot-password"
                      className="text-[11px] text-[#adc6ff] hover:underline"
                    >
                      Forgot password?
                    </Link>
                  </div>
                  <PasswordInput
                    id="login-password"
                    placeholder="Enter your password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    error={passwordError}
                    autoComplete="current-password"
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
                  Log in
                </Button>
              </form>

              {/* Divider */}
              <div className="relative flex items-center justify-center my-4">
                <div className="absolute inset-0 flex items-center">
                  <div className="w-full border-t border-[#23252a]" />
                </div>
                <span className="relative px-3 bg-[#141618] text-[10px] font-mono text-[#6b7280] uppercase tracking-wider">
                  OR
                </span>
              </div>

              {/* Social Login Buttons (UI Only) */}
              <div className="space-y-2">
                <button
                  type="button"
                  onClick={() => {
                    // Informative UI state without faking OAuth
                    setFormError("Social authentication will be enabled with backend OAuth in the next phase. Use Email sign in or Explore Workspace below.");
                  }}
                  className="w-full h-9 rounded-lg bg-[#1a1c20] hover:bg-[#22242a] text-[#d1d5db] border border-[#2b2e35] text-xs font-medium flex items-center justify-center gap-2 transition-colors cursor-pointer"
                >
                  <svg className="w-4 h-4" viewBox="0 0 24 24">
                    <path
                      fill="#EA4335"
                      d="M12 5c1.6 0 3 .6 4.1 1.7l3.1-3.1C17.3 1.8 14.8 1 12 1 7.4 1 3.5 3.6 1.6 7.4l3.7 2.9C6.2 7.3 8.9 5 12 5z"
                    />
                    <path
                      fill="#4285F4"
                      d="M23.5 12.3c0-.8-.1-1.7-.2-2.3H12v4.6h6.5c-.3 1.5-1.1 2.8-2.4 3.7l3.7 2.9c2.2-2 3.7-5 3.7-8.9z"
                    />
                    <path
                      fill="#FBBC05"
                      d="M5.3 14.7c-.2-.7-.4-1.5-.4-2.7s.1-2 .4-2.7L1.6 6.4C.6 8.3 0 10.1 0 12s.6 3.7 1.6 5.6l3.7-2.9z"
                    />
                    <path
                      fill="#34A853"
                      d="M12 23c3.2 0 6-1.1 8-3l-3.7-2.9c-1.1.7-2.5 1.2-4.3 1.2-3.1 0-5.8-2.3-6.7-5.3L1.6 16C3.5 19.8 7.4 23 12 23z"
                    />
                  </svg>
                  <span>Continue with Google</span>
                </button>

                <button
                  type="button"
                  onClick={() => {
                    setFormError("GitHub OAuth will be connected with repository permissions in the next phase. Use Email sign in or Explore Workspace below.");
                  }}
                  className="w-full h-9 rounded-lg bg-[#1a1c20] hover:bg-[#22242a] text-[#d1d5db] border border-[#2b2e35] text-xs font-medium flex items-center justify-center gap-2 transition-colors cursor-pointer"
                >
                  <svg className="w-4 h-4 fill-current text-[#f3f4f6]" viewBox="0 0 24 24">
                    <path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0024 12c0-6.63-5.37-12-12-12z" />
                  </svg>
                  <span>Continue with GitHub</span>
                </button>
              </div>

              {/* Direct Workspace Preview Link */}
              <div className="pt-2 text-center">
                <Link
                  href="/app"
                  className="inline-flex items-center gap-1.5 text-xs text-[#adc6ff] hover:text-white transition-colors font-medium"
                >
                  <span>Direct workspace preview</span>
                  <ArrowRight className="w-3 h-3" />
                </Link>
              </div>

              {/* Bottom Footer */}
              <div className="pt-4 border-t border-[#23252a] text-center text-xs text-[#9ca3af]">
                <span>Don&apos;t have an account? </span>
                <Link
                  href="/signup"
                  className="text-[#3B82F6] hover:text-[#60a5fa] font-medium hover:underline"
                >
                  Create account
                </Link>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Footer */}
      <div className="p-4 text-center text-xs text-[#6b7280] border-t border-[#1c1e22]">
        DevMind AI • AI Codebase Intelligence
      </div>
    </div>
  );
}
