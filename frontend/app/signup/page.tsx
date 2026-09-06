"use client";

import React, { useState, useRef } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Logo } from "@/components/public/Logo";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { PasswordInput } from "@/components/ui/PasswordInput";
import { PasswordStrength } from "@/components/ui/PasswordStrength";
import { User, Mail, ShieldAlert, ArrowRight } from "lucide-react";
import {
  registerUser,
  loginUser,
  setStoredAuthToken,
  setStoredUser,
  ValidationError,
} from "@/lib/api-client";

export default function SignupPage() {
  const router = useRouter();
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");

  const [fullNameError, setFullNameError] = useState("");
  const [emailError, setEmailError] = useState("");
  const [passwordError, setPasswordError] = useState("");
  const [confirmPasswordError, setConfirmPasswordError] = useState("");
  const [formError, setFormError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const validate = () => {
    let valid = true;
    setFullNameError("");
    setEmailError("");
    setPasswordError("");
    setConfirmPasswordError("");
    setFormError(null);

    if (!fullName.trim()) {
      setFullNameError("Please enter your full name.");
      valid = false;
    }

    if (!email.trim()) {
      setEmailError("Please enter your email address.");
      valid = false;
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      setEmailError("Please enter a valid email address.");
      valid = false;
    }

    if (!password) {
      setPasswordError("Please enter a password.");
      valid = false;
    } else if (password.length < 8) {
      setPasswordError("Password must be at least 8 characters long.");
      valid = false;
    }

    if (!confirmPassword) {
      setConfirmPasswordError("Please confirm your password.");
      valid = false;
    } else if (password !== confirmPassword) {
      setConfirmPasswordError("Passwords do not match.");
      valid = false;
    }

    return valid;
  };

  const isSubmittingRef = useRef(false);

  const handleSignup = async (e: React.FormEvent) => {
    e.preventDefault();
    if (isSubmittingRef.current || isLoading) return;
    if (!validate()) return;

    isSubmittingRef.current = true;
    setIsLoading(true);
    setFormError(null);

    try {
      // 1. Call real POST /auth/register
      await registerUser({
        email: email.trim(),
        password,
        full_name: fullName.trim() || undefined,
      });

      // 2. Authenticate immediately to acquire real JWT access token
      const authRes = await loginUser({ email: email.trim(), password });
      setStoredAuthToken(authRes.access_token);
      setStoredUser(authRes.user);

      // 3. Move to /app
      router.push("/app");
    } catch (err: any) {
      if (err.status === 409 || err.message?.includes("already exists")) {
        setFormError("An account with this email address already exists.");
      } else if (err instanceof ValidationError) {
        setFormError(err.message || "Please check the entered values.");
      } else {
        setFormError(err.message || "Registration failed. Please check your connection and try again.");
      }
    } finally {
      setIsLoading(false);
      isSubmittingRef.current = false;
    }
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
        <div className="w-full max-w-[440px] rounded-2xl bg-[#141618] border border-[#23252a] p-6 sm:p-8 shadow-[0_8px_30px_rgba(0,0,0,0.5)] space-y-5">
          {/* Header */}
          <div className="space-y-1.5 text-center sm:text-left">
            <h1 className="text-xl sm:text-2xl font-semibold text-[#f3f4f6] tracking-tight">
              Create your DevMind AI account
            </h1>
            <p className="text-xs sm:text-sm text-[#9ca3af]">
              Start understanding your codebase with AI.
            </p>
          </div>

          {/* Form Error */}
          {formError && (
            <div
              role="alert"
              className="p-3 rounded-lg bg-[#ef4444]/15 border border-[#ef4444]/30 text-xs text-[#fca5a5] flex items-center gap-2 animate-fade-in-up"
            >
              <ShieldAlert className="w-4 h-4 shrink-0 text-[#ef4444]" />
              <span>{formError}</span>
            </div>
          )}

          {/* Signup Form */}
          <form onSubmit={handleSignup} className="space-y-3.5" noValidate>
            <Input
              id="signup-fullname"
              name="fullName"
              label="Full name"
              type="text"
              placeholder="Ada Lovelace"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              error={fullNameError}
              leftIcon={<User className="w-4 h-4 text-[#6b7280]" />}
              autoComplete="name"
              disabled={isLoading}
            />

            <Input
              id="signup-email"
              name="email"
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

            <div className="space-y-1">
              <label
                htmlFor="signup-password"
                className="text-xs font-medium text-[#d1d5db]"
              >
                Password
              </label>
              <PasswordInput
                id="signup-password"
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
                htmlFor="signup-confirm-password"
                className="text-xs font-medium text-[#d1d5db]"
              >
                Confirm password
              </label>
              <PasswordInput
                id="signup-confirm-password"
                placeholder="Re-enter your password"
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
              Create account
            </Button>
          </form>

          {/* Terms Note */}
          <p className="text-[11px] text-[#6b7280] text-center leading-relaxed">
            By creating an account, you agree to the{" "}
            <a href="#terms" className="text-[#9ca3af] hover:underline">
              Terms of Service
            </a>{" "}
            and{" "}
            <a href="#privacy" className="text-[#9ca3af] hover:underline">
              Privacy Policy
            </a>
            .
          </p>

          {/* Divider */}
          <div className="relative flex items-center justify-center my-3">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-[#23252a]" />
            </div>
            <span className="relative px-3 bg-[#141618] text-[10px] font-mono text-[#6b7280] uppercase tracking-wider">
              OR
            </span>
          </div>

          {/* Social UI */}
          <div className="space-y-2">
            <button
              type="button"
              onClick={() =>
                setFormError("Social sign up will connect to OAuth in the next phase. Use Email registration above.")
              }
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
              onClick={() =>
                setFormError("GitHub OAuth registration will be connected in the next phase. Use Email registration above.")
              }
              className="w-full h-9 rounded-lg bg-[#1a1c20] hover:bg-[#22242a] text-[#d1d5db] border border-[#2b2e35] text-xs font-medium flex items-center justify-center gap-2 transition-colors cursor-pointer"
            >
              <svg className="w-4 h-4 fill-current text-[#f3f4f6]" viewBox="0 0 24 24">
                <path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0024 12c0-6.63-5.37-12-12-12z" />
              </svg>
              <span>Continue with GitHub</span>
            </button>
          </div>

          {/* Footer */}
          <div className="pt-4 border-t border-[#23252a] text-center text-xs text-[#9ca3af]">
            <span>Already have an account? </span>
            <Link
              href="/login"
              className="text-[#3B82F6] hover:text-[#60a5fa] font-medium hover:underline"
            >
              Log in
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
