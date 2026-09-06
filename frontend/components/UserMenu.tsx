"use client";

import React, { useState } from "react";
import Link from "next/link";
import { User, LogOut, Settings, ShieldCheck, ChevronUp } from "lucide-react";

interface UserMenuProps {
  userName?: string;
  userEmail?: string;
  onOpenSettings?: () => void;
  onLogout?: () => void;
}

export function UserMenu({
  userName = "Developer Workspace",
  userEmail = "dev@workspace.local",
  onOpenSettings,
  onLogout,
}: UserMenuProps) {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <div className="relative font-sans text-xs">
      {/* Trigger Button */}
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        aria-expanded={isOpen}
        aria-label="User profile menu"
        className="w-full flex items-center justify-between p-2 rounded-lg hover:bg-[#1C1C1C] border border-transparent hover:border-[#2A2A2A] transition-colors cursor-pointer group text-left"
      >
        <div className="flex items-center gap-2.5 min-w-0">
          <div className="w-7 h-7 rounded-full bg-[#232730] border border-[#343842] flex items-center justify-center text-[#adc6ff] shrink-0 font-medium text-xs">
            <User className="w-3.5 h-3.5" />
          </div>
          <div className="min-w-0 flex-1">
            <p className="font-medium text-[#e2e2e2] text-xs truncate group-hover:text-white">
              {userName}
            </p>
            <p className="text-[10px] text-[#8c909f] truncate font-mono">
              {userEmail}
            </p>
          </div>
        </div>
        <ChevronUp
          className={`w-3.5 h-3.5 text-[#8c909f] transition-transform ${
            isOpen ? "rotate-180" : ""
          }`}
        />
      </button>

      {/* Popover Menu */}
      {isOpen && (
        <div className="absolute bottom-full left-0 mb-1.5 w-full rounded-xl bg-[#171717] border border-[#2A2A2A] p-1.5 shadow-xl space-y-0.5 z-30 animate-fade-in-up">
          <div className="px-2.5 py-1.5 border-b border-[#2A2A2A] mb-1">
            <p className="text-[10px] font-mono text-[#8c909f]">SESSION PROFILE</p>
            <p className="text-xs font-semibold text-[#f3f4f6] truncate">{userName}</p>
          </div>

          {onOpenSettings && (
            <button
              type="button"
              onClick={() => {
                setIsOpen(false);
                onOpenSettings();
              }}
              className="w-full flex items-center gap-2 px-2.5 py-1.5 rounded-lg hover:bg-[#282a2b] text-[#d1d5db] hover:text-white transition-colors cursor-pointer text-left"
            >
              <Settings className="w-3.5 h-3.5 text-[#8c909f]" />
              <span>Workspace Settings</span>
            </button>
          )}

          <Link
            href="/"
            onClick={() => setIsOpen(false)}
            className="w-full flex items-center gap-2 px-2.5 py-1.5 rounded-lg hover:bg-[#282a2b] text-[#d1d5db] hover:text-white transition-colors text-left"
          >
            <ShieldCheck className="w-3.5 h-3.5 text-[#3B82F6]" />
            <span>Public Website</span>
          </Link>

          {onLogout ? (
            <button
              type="button"
              onClick={() => {
                setIsOpen(false);
                onLogout();
              }}
              className="w-full flex items-center gap-2 px-2.5 py-1.5 rounded-lg hover:bg-[#ef4444]/15 text-[#fca5a5] transition-colors cursor-pointer text-left"
            >
              <LogOut className="w-3.5 h-3.5 text-[#ef4444]" />
              <span>Sign Out / Switch</span>
            </button>
          ) : (
            <Link
              href="/login"
              onClick={() => setIsOpen(false)}
              className="w-full flex items-center gap-2 px-2.5 py-1.5 rounded-lg hover:bg-[#ef4444]/15 text-[#fca5a5] transition-colors text-left"
            >
              <LogOut className="w-3.5 h-3.5 text-[#ef4444]" />
              <span>Sign Out / Switch</span>
            </Link>
          )}
        </div>
      )}
    </div>
  );
}
