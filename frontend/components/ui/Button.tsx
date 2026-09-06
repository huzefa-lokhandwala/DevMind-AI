"use client";

import React, { forwardRef } from "react";
import { Loader2 } from "lucide-react";

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary" | "outline" | "ghost" | "danger";
  size?: "sm" | "md" | "lg";
  isLoading?: boolean;
  fullWidth?: boolean;
  leftIcon?: React.ReactNode;
  rightIcon?: React.ReactNode;
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      children,
      variant = "primary",
      size = "md",
      isLoading = false,
      fullWidth = false,
      leftIcon,
      rightIcon,
      className = "",
      disabled,
      ...props
    },
    ref
  ) => {
    const baseStyles =
      "inline-flex items-center justify-center font-medium transition-all select-none cursor-pointer rounded-lg disabled:opacity-50 disabled:cursor-not-allowed disabled:pointer-events-none focus:outline-none focus-visible:ring-2 focus-visible:ring-[#3B82F6] focus-visible:ring-offset-2 focus-visible:ring-offset-[#111111] active:scale-[0.98]";

    const sizeStyles = {
      sm: "h-8 px-3 text-xs gap-1.5",
      md: "h-9 px-4 text-xs md:text-sm gap-2",
      lg: "h-11 px-5 text-sm md:text-base gap-2.5",
    }[size];

    const variantStyles = {
      primary:
        "bg-[#3B82F6] hover:bg-[#2563eb] text-white shadow-[0_1px_3px_rgba(0,0,0,0.3)] border border-[#3B82F6]/30",
      secondary:
        "bg-[#1c1e22] hover:bg-[#26282e] text-[#f3f4f6] border border-[#2b2e35]",
      outline:
        "bg-transparent hover:bg-[#1c1e22] text-[#e5e7eb] border border-[#2b2e35] hover:border-[#3b82f6]/40",
      ghost:
        "bg-transparent hover:bg-[#1a1c20] text-[#9ca3af] hover:text-[#f3f4f6]",
      danger:
        "bg-[#ef4444]/15 hover:bg-[#ef4444]/25 text-[#fca5a5] border border-[#ef4444]/30",
    }[variant];

    const widthStyle = fullWidth ? "w-full" : "";

    return (
      <button
        ref={ref}
        disabled={disabled || isLoading}
        className={`${baseStyles} ${sizeStyles} ${variantStyles} ${widthStyle} ${className}`}
        {...props}
      >
        {isLoading ? (
          <>
            <Loader2 className="w-4 h-4 animate-spin text-current" />
            <span>{children}</span>
          </>
        ) : (
          <>
            {leftIcon && <span className="shrink-0">{leftIcon}</span>}
            <span>{children}</span>
            {rightIcon && <span className="shrink-0">{rightIcon}</span>}
          </>
        )}
      </button>
    );
  }
);

Button.displayName = "Button";
