"use client";
import { Bell, Sparkles } from "lucide-react";

interface TopBarProps {
  title: string;
  subtitle?: string;
}

export default function TopBar({ title, subtitle }: TopBarProps) {
  return (
    <header className="flex items-center justify-between px-6 py-4 border-b border-[var(--border)] bg-white/80 backdrop-blur-sm flex-shrink-0 sticky top-0 z-20">
      <div className="flex items-center gap-3">
        <div>
          <h1 className="font-display font-semibold text-[17px] text-[var(--text)] leading-tight">{title}</h1>
          {subtitle && <p className="text-[11px] text-[var(--text-3)] mt-0.5">{subtitle}</p>}
        </div>
      </div>

      <div className="flex items-center gap-2.5">
        {/* AI badge */}
        <div className="hidden sm:flex items-center gap-1.5 bg-amber-50 border border-amber-200 rounded-full px-3 py-1">
          <Sparkles size={11} className="text-amber-600" />
          <span className="text-[11px] font-semibold text-amber-700">AI Assistant</span>
        </div>

        {/* Notification */}
        <button className="relative w-8 h-8 rounded-xl bg-[var(--surface-alt)] border border-[var(--border)] flex items-center justify-center text-[var(--text-3)] hover:text-[var(--text)] hover:border-[var(--border-strong)] transition-all">
          <Bell size={14} />
          <span className="absolute top-1.5 right-1.5 w-1.5 h-1.5 rounded-full bg-amber-500" />
        </button>

        {/* User avatar */}
        <div
          className="w-8 h-8 rounded-xl flex items-center justify-center cursor-pointer text-white font-bold text-xs flex-shrink-0"
          style={{ background: "linear-gradient(135deg,#D97706 0%,#92400E 100%)" }}
        >
          A
        </div>
      </div>
    </header>
  );
}
