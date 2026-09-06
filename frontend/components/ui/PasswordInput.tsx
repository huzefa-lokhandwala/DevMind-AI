"use client";

import React, { useState, forwardRef } from "react";
import { Eye, EyeOff, Lock } from "lucide-react";
import { Input, InputProps } from "./Input";

export interface PasswordInputProps extends Omit<InputProps, "type" | "rightElement"> {
  showLockIcon?: boolean;
}

export const PasswordInput = forwardRef<HTMLInputElement, PasswordInputProps>(
  ({ showLockIcon = true, ...props }, ref) => {
    const [showPassword, setShowPassword] = useState(false);

    const toggleVisibility = () => {
      setShowPassword((prev) => !prev);
    };

    const toggleButton = (
      <button
        type="button"
        onClick={toggleVisibility}
        aria-label={showPassword ? "Hide password" : "Show password"}
        aria-pressed={showPassword}
        className="p-1 rounded text-[#9ca3af] hover:text-[#f3f4f6] hover:bg-[#1f2227] transition-colors cursor-pointer focus:outline-none focus:ring-1 focus:ring-[#3B82F6]"
      >
        {showPassword ? (
          <EyeOff className="w-4 h-4 text-[#9ca3af]" />
        ) : (
          <Eye className="w-4 h-4 text-[#9ca3af]" />
        )}
      </button>
    );

    return (
      <Input
        ref={ref}
        type={showPassword ? "text" : "password"}
        leftIcon={showLockIcon ? <Lock className="w-4 h-4 text-[#6b7280]" /> : undefined}
        rightElement={toggleButton}
        {...props}
      />
    );
  }
);

PasswordInput.displayName = "PasswordInput";
