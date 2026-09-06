"use client";

import React from "react";
import { Logo } from "@/components/public/Logo";

interface AuthCardProps {
  title: string;
  subtitle?: string;
  children: React.ReactNode;
  footer?: React.ReactNode;
  showLogo?: boolean;
}

export function AuthCard({
  title,
  subtitle,
  children,
  footer,
  showLogo = true,
}: AuthCardProps) {
  return (
    <div className="w-full max-w-[420px] rounded-2xl bg-[#141618] border border-[#23252a] p-6 sm:p-8 shadow-[0_8px_30px_rgba(0,0,0,0.5)] font-sans text-left relative">
      {/* Top Header */}
      <div className="space-y-3 mb-6">
        {showLogo && (
          <div className="mb-4">
            <Logo size="md" />
          </div>
        )}
        <h1 className="text-xl sm:text-2xl font-semibold text-[#f3f4f6] tracking-tight">
          {title}
        </h1>
        {subtitle && (
          <p className="text-xs sm:text-sm text-[#9ca3af] leading-relaxed">
            {subtitle}
          </p>
        )}
      </div>

      {/* Card Content */}
      <div className="space-y-4">{children}</div>

      {/* Card Footer */}
      {footer && (
        <div className="mt-6 pt-5 border-t border-[#23252a] text-center text-xs text-[#9ca3af]">
          {footer}
        </div>
      )}
    </div>
  );
}
