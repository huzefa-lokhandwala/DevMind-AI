import type { Metadata } from "next";
import { Inter, JetBrains_Mono } from "next/font/google";
import "./globals.css";

const inter = Inter({
  variable: "--font-inter",
  subsets: ["latin"],
  display: "swap",
});

const jetbrainsMono = JetBrains_Mono({
  variable: "--font-mono",
  subsets: ["latin"],
  display: "swap",
});

export const metadata: Metadata = {
  title: "DevMind AI - Developer Workspace",
  description: "Code-Aware RAG Platform for Codebase Reasoning and AST Hybrid Retrieval",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${inter.variable} ${jetbrainsMono.variable} dark h-full antialiased`}
    >
      <body className="h-full bg-[#111111] text-[#e2e2e2] flex flex-col font-sans selection:bg-[#3B82F6]/30 selection:text-[#adc6ff]">
        {children}
      </body>
    </html>
  );
}
