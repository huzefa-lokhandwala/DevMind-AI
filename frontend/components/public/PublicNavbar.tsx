"use client";

import React, { useState } from "react";
import Link from "next/link";
import { Logo } from "./Logo";
import { Menu, X, ArrowRight } from "lucide-react";

export function PublicNavbar() {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const navLinks = [
    { label: "Product", href: "#product" },
    { label: "How It Works", href: "#how-it-works" },
    { label: "Technology", href: "#technology" },
    { label: "Capabilities", href: "#capabilities" },
  ];

  return (
    <header className="sticky top-0 z-50 w-full border-b border-[#23252a] bg-[#0c0d0e]/85 backdrop-blur-md font-sans">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        {/* Brand */}
        <Logo size="md" href="/" />

        {/* Desktop Navigation */}
        <nav className="hidden md:flex items-center gap-7 text-xs sm:text-sm font-medium text-[#9ca3af]">
          {navLinks.map((link) => (
            <a
              key={link.label}
              href={link.href}
              className="hover:text-[#f3f4f6] transition-colors py-2"
            >
              {link.label}
            </a>
          ))}
        </nav>

        {/* Right CTA Actions */}
        <div className="hidden md:flex items-center gap-3">
          <Link
            href="/login"
            className="text-xs sm:text-sm font-medium text-[#d1d5db] hover:text-white px-3 py-2 transition-colors"
          >
            Log in
          </Link>
          <Link
            href="/login"
            className="h-9 px-4 rounded-lg bg-[#3B82F6] hover:bg-[#2563eb] text-white text-xs sm:text-sm font-medium transition-all shadow-sm flex items-center gap-1.5 active:scale-[0.98]"
          >
            <span>Let&apos;s Try DevMind AI</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </Link>
        </div>

        {/* Mobile Hamburger Button */}
        <button
          type="button"
          onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
          aria-label={mobileMenuOpen ? "Close menu" : "Open menu"}
          aria-expanded={mobileMenuOpen}
          className="md:hidden p-2 rounded-lg text-[#9ca3af] hover:text-[#f3f4f6] hover:bg-[#1a1c20] transition-colors focus:outline-none focus:ring-1 focus:ring-[#3B82F6]"
        >
          {mobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
        </button>
      </div>

      {/* Mobile Menu Drawer */}
      {mobileMenuOpen && (
        <div className="md:hidden border-b border-[#23252a] bg-[#111315] px-4 pt-3 pb-5 space-y-3 animate-fade-in-up">
          <nav className="flex flex-col space-y-2">
            {navLinks.map((link) => (
              <a
                key={link.label}
                href={link.href}
                onClick={() => setMobileMenuOpen(false)}
                className="px-3 py-2 rounded-lg text-sm text-[#d1d5db] hover:bg-[#1a1c20] hover:text-white transition-colors"
              >
                {link.label}
              </a>
            ))}
          </nav>
          <div className="pt-3 border-t border-[#23252a] flex flex-col gap-2">
            <Link
              href="/login"
              onClick={() => setMobileMenuOpen(false)}
              className="w-full text-center py-2 text-sm text-[#d1d5db] hover:text-white font-medium"
            >
              Log in
            </Link>
            <Link
              href="/login"
              onClick={() => setMobileMenuOpen(false)}
              className="w-full h-10 rounded-lg bg-[#3B82F6] hover:bg-[#2563eb] text-white text-sm font-medium flex items-center justify-center gap-2 active:scale-[0.98]"
            >
              <span>Let&apos;s Try DevMind AI</span>
              <ArrowRight className="w-4 h-4" />
            </Link>
          </div>
        </div>
      )}
    </header>
  );
}
