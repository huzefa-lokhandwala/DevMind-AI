"use client";

import React from "react";

interface PasswordStrengthProps {
  password: string;
}

export function getPasswordStrength(password: string): {
  score: number;
  label: string;
  color: string;
} {
  if (!password) {
    return { score: 0, label: "", color: "bg-[#262930]" };
  }

  let score = 0;
  if (password.length >= 8) score++;
  if (/[a-z]/.test(password) && /[A-Z]/.test(password)) score++;
  if (/\d/.test(password)) score++;
  if (/[^a-zA-Z0-9]/.test(password) || password.length >= 12) score++;

  if (score <= 1) {
    return { score: 1, label: "Weak", color: "bg-[#ef4444]" };
  }
  if (score === 2) {
    return { score: 2, label: "Fair", color: "bg-[#f59e0b]" };
  }
  if (score === 3) {
    return { score: 3, label: "Good", color: "bg-[#3b82f6]" };
  }
  return { score: 4, label: "Strong", color: "bg-[#10b981]" };
}

export function PasswordStrength({ password }: PasswordStrengthProps) {
  if (!password) return null;

  const { score, label, color } = getPasswordStrength(password);

  return (
    <div className="space-y-1 pt-1" aria-live="polite">
      <div className="flex items-center justify-between text-[11px]">
        <span className="text-[#9ca3af]">Password strength</span>
        <span className="font-medium text-[#d1d5db]">{label}</span>
      </div>
      <div className="grid grid-cols-4 gap-1.5 h-1">
        {[1, 2, 3, 4].map((index) => (
          <div
            key={index}
            className={`h-full rounded-full transition-all duration-300 ${
              index <= score ? color : "bg-[#262930]"
            }`}
          />
        ))}
      </div>
    </div>
  );
}
