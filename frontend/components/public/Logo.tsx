"use client";

import Link from "next/link";

interface LogoProps {
  size?: "sm" | "md" | "lg";
  href?: string;
  showBadge?: boolean;
}

export function Logo({ size = "md", href = "/", showBadge = true }: LogoProps) {
  const iconSize = size === "sm" ? "w-6 h-6" : size === "lg" ? "w-9 h-9" : "w-7 h-7";
  const textSize = size === "sm" ? "text-sm" : size === "lg" ? "text-xl" : "text-base";

  const content = (
    <div className="flex items-center gap-2.5 group cursor-pointer select-none">
      {/* DevMind Technical Glyphic Mark */}
      <div
        className={`${iconSize} rounded-lg bg-[#141618] border border-[#26282d] group-hover:border-[#3B82F6]/60 flex items-center justify-center text-[#adc6ff] transition-all shadow-[0_2px_8px_rgba(0,0,0,0.4)] relative overflow-hidden`}
      >
        <div className="absolute inset-0 bg-gradient-to-br from-[#3B82F6]/10 to-transparent opacity-0 group-hover:opacity-100 transition-opacity" />
        <svg
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2.2"
          strokeLinecap="round"
          strokeLinejoin="round"
          className="w-4 h-4 text-[#3B82F6] transition-transform group-hover:scale-105"
        >
          {/* Stylized code brackets with central neural node */}
          <path d="M16 18l6-6-6-6" />
          <path d="M8 6l-6 6 6 6" />
          <circle cx="12" cy="12" r="1.5" fill="#adc6ff" stroke="none" />
        </svg>
      </div>

      <div className="flex items-center gap-1.5">
        <span className={`${textSize} font-semibold text-[#f3f4f6] tracking-tight leading-none group-hover:text-white transition-colors font-sans`}>
          DevMind
        </span>
        {showBadge && (
          <span className="text-[10px] font-mono font-medium tracking-wider px-1.5 py-0.5 rounded bg-[#182338] text-[#adc6ff] border border-[#3B82F6]/30 leading-none">
            AI
          </span>
        )}
      </div>
    </div>
  );

  if (href) {
    return (
      <Link href={href} className="inline-flex items-center">
        {content}
      </Link>
    );
  }

  return content;
}
