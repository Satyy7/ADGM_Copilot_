"use client";
import { Bell, Search, User } from "lucide-react";
import { useState } from "react";

interface TopBarProps {
  title: string;
  subtitle?: string;
}

export default function TopBar({ title, subtitle }: TopBarProps) {
  const [search, setSearch] = useState("");

  return (
    <header className="flex items-center justify-between px-6 py-4 border-b border-white/5 bg-navy-900/60 backdrop-blur-md flex-shrink-0">
      <div>
        <h1 className="text-lg font-semibold text-white">{title}</h1>
        {subtitle && <p className="text-xs text-slate-500 mt-0.5">{subtitle}</p>}
      </div>

      <div className="flex items-center gap-3">
        {/* Search bar */}
        <div className="relative hidden md:flex items-center">
          <Search className="absolute left-3 text-slate-500 w-3.5 h-3.5" />
          <input
            type="text"
            placeholder="Quick search…"
            value={search}
            onChange={e => setSearch(e.target.value)}
            className="w-52 bg-navy-800/80 border border-white/8 rounded-xl pl-9 pr-4 py-1.5 text-sm text-slate-300 placeholder:text-slate-600 focus:outline-none focus:border-gold-500/40 focus:bg-navy-800 transition-all"
          />
        </div>

        {/* Notifications */}
        <button className="relative w-9 h-9 rounded-xl bg-navy-800/80 border border-white/8 flex items-center justify-center text-slate-400 hover:text-slate-200 hover:border-gold-500/20 transition-all">
          <Bell size={15} />
          <span className="absolute top-1.5 right-1.5 w-1.5 h-1.5 rounded-full bg-gold-400" />
        </button>

        {/* User avatar */}
        <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-gold-400/20 to-gold-600/10 border border-gold-500/25 flex items-center justify-center cursor-pointer hover:border-gold-500/40 transition-all">
          <User size={15} className="text-gold-400" />
        </div>
      </div>
    </header>
  );
}
