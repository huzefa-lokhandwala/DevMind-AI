"use client";

import React, { forwardRef, useId } from "react";

export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
  helperText?: string;
  leftIcon?: React.ReactNode;
  rightElement?: React.ReactNode;
}

export const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ label, error, helperText, leftIcon, rightElement, className = "", id, ...props }, ref) => {
    const generatedId = useId();
    const inputId = id || generatedId;
    const errorId = `${inputId}-error`;
    const helperId = `${inputId}-helper`;

    return (
      <div className="w-full space-y-1.5 font-sans text-left">
        {label && (
          <label
            htmlFor={inputId}
            className="block text-xs font-medium text-[#d1d5db] select-none"
          >
            {label}
          </label>
        )}

        <div className="relative flex items-center">
          {leftIcon && (
            <div className="absolute left-3 text-[#6b7280] pointer-events-none flex items-center">
              {leftIcon}
            </div>
          )}

          <input
            ref={ref}
            id={inputId}
            aria-invalid={!!error}
            aria-describedby={error ? errorId : helperText ? helperId : undefined}
            className={`w-full h-9 rounded-lg bg-[#111315] border text-xs md:text-sm text-[#f3f4f6] placeholder-[#6b7280] transition-colors focus:outline-none focus:ring-1 focus:ring-[#3B82F6] ${
              leftIcon ? "pl-9" : "pl-3"
            } ${rightElement ? "pr-10" : "pr-3"} ${
              error
                ? "border-[#ef4444] focus:border-[#ef4444] focus:ring-[#ef4444]"
                : "border-[#262930] hover:border-[#373b45] focus:border-[#3B82F6]"
            } disabled:opacity-50 disabled:bg-[#181a1d] disabled:cursor-not-allowed ${className}`}
            {...props}
          />

          {rightElement && (
            <div className="absolute right-2.5 flex items-center">{rightElement}</div>
          )}
        </div>

        {error ? (
          <p id={errorId} role="alert" className="text-[11px] text-[#f87171] font-medium animate-fade-in-up">
            {error}
          </p>
        ) : helperText ? (
          <p id={helperId} className="text-[11px] text-[#9ca3af]">
            {helperText}
          </p>
        ) : null}
      </div>
    );
  }
);

Input.displayName = "Input";
