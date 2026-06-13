"use client";
import Link from "next/link";
import {
  MessageSquare, FileSearch, FileText, BarChart3,
  Gavel, ArrowRight, Database,
  TrendingUp, Sparkles,
} from "lucide-react";
import { useEffect, useState } from "react";
import TopBar from "@/components/layout/TopBar";
import { getCacheStats } from "@/lib/api";
import type { CacheStats } from "@/types";

const CAPABILITIES = [
  {
    href: "/chat",
    icon: MessageSquare,
    title: "AI Copilot",
    description: "Ask any ADGM regulatory question and get precise, cited answers from the official knowledge base.",
    badge: "Intelligent Q&A",
    accent: "#D97706",
    bg: "#FFFBEB",
    border: "#FDE68A",
  },
  {
    href: "/review",
    icon: FileSearch,
    title: "Document Review",
    description: "Upload PDF or DOCX. Six specialist AI agents analyse violations, gaps, and generate a compliance score.",
    badge: "Automated Analysis",
    accent: "#0284C7",
    bg: "#F0F9FF",
    border: "#BAE6FD",
  },
  {
    href: "/clauses",
    icon: FileText,
    title: "Clause Generator",
    description: "Draft ADGM-compliant legal clauses with precise article references for contracts or articles of association.",
    badge: "Cited Drafting",
    accent: "#7C3AED",
    bg: "#F5F3FF",
    border: "#DDD6FE",
  },
  {
    href: "/analytics",
    icon: BarChart3,
    title: "Analytics",
    description: "Ask data questions in plain English. The AI generates a query, shows a preview, and waits for your approval.",
    badge: "Natural Language Queries",
    accent: "#EA580C",
    bg: "#FFF7ED",
    border: "#FED7AA",
  },
  {
    href: "/cases",
    icon: Gavel,
    title: "Case Search",
    description: "Find historical compliance reviews matching your scenario using intelligent semantic search.",
    badge: "Semantic Search",
    accent: "#DB2777",
    bg: "#FDF2F8",
    border: "#FBCFE8",
  },
];


export default function DashboardPage() {
  const [cache, setCache] = useState<CacheStats | null>(null);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
    getCacheStats().then(setCache).catch(() => null);
  }, []);

  return (
    <div className="flex flex-col h-full overflow-hidden">
      <TopBar title="Dashboard" subtitle="ADGM Compliance Intelligence Platform" />

      <div className="flex-1 overflow-y-auto px-6 py-6 space-y-7 page-enter">

        {/* Hero banner */}
        <div
          className="relative overflow-hidden rounded-2xl border border-amber-200 px-8 py-7"
          style={{ background: "linear-gradient(135deg, #FFFBEB 0%, #FEF9F0 50%, #FEFDF5 100%)" }}
        >
          {/* Decorative circles */}
          <div className="absolute -top-10 -right-10 w-52 h-52 rounded-full bg-amber-100/60 blur-2xl pointer-events-none" />
          <div className="absolute -bottom-8 -left-8 w-36 h-36 rounded-full bg-amber-50 blur-xl pointer-events-none" />

          <div className="relative flex flex-col sm:flex-row sm:items-center justify-between gap-5">
            <div>
              <div className="flex items-center gap-2 mb-3">
                <div className="status-dot" />
                <span className="text-[11px] font-semibold text-amber-700 tracking-wide uppercase">All systems operational</span>
              </div>
              <h2 className="font-display text-3xl font-bold text-[var(--text)] mb-2 leading-tight">
                Welcome to <span className="text-amber-700">ADGM Nexus</span>
              </h2>
              <p className="text-sm text-[var(--text-2)] max-w-md leading-relaxed">
                Enterprise-grade AI compliance platform for the Abu Dhabi Global Market.
                Ask questions, review documents, draft clauses, run analytics, and search precedents — all in one place.
              </p>
            </div>
            <Link href="/chat">
              <button className="btn-amber flex items-center gap-2 whitespace-nowrap">
                <Sparkles size={14} /> Start Chatting <ArrowRight size={14} />
              </button>
            </Link>
          </div>
        </div>

        {/* Capabilities */}
        <div>
          <div className="flex items-center gap-2 mb-4">
            <TrendingUp size={14} className="text-[var(--text-3)]" />
            <p className="section-label">Capabilities</p>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
            {CAPABILITIES.map(({ href, icon: Icon, title, description, badge, accent, bg, border }) => (
              <Link key={href} href={href}>
                <div className="card card-hover p-5 h-full cursor-pointer group relative overflow-hidden">
                  {/* Top accent stripe */}
                  <div className="absolute top-0 left-0 right-0 h-[3px] rounded-t-2xl" style={{ background: accent }} />

                  <div className="flex items-start justify-between mb-3 pt-1">
                    <div
                      className="w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0"
                      style={{ background: bg, border: `1.5px solid ${border}` }}
                    >
                      <Icon size={17} style={{ color: accent }} />
                    </div>
                    <ArrowRight
                      size={13}
                      className="text-[var(--text-3)] group-hover:translate-x-1 transition-transform duration-200 mt-1"
                      style={{ color: accent }}
                    />
                  </div>

                  <h4 className="font-display text-[14.5px] font-semibold text-[var(--text)] mb-1.5 group-hover:text-amber-700 transition-colors">
                    {title}
                  </h4>
                  <p className="text-[12.5px] text-[var(--text-2)] leading-relaxed mb-3">{description}</p>
                  <span
                    className="badge text-[10px]"
                    style={{ background: bg, borderColor: border, color: accent }}
                  >
                    {badge}
                  </span>
                </div>
              </Link>
            ))}
          </div>
        </div>

        {/* Cache stats */}
        {cache && (
          <div className="card p-5">
            <div className="flex items-center gap-2 mb-4">
              <Database size={14} className="text-[var(--text-3)]" />
              <p className="section-label">Performance Cache</p>
            </div>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              {[
                { label: "Embeddings Cached",  value: cache.namespaces.embeddings,    accent: "#D97706", bg: "#FFFBEB" },
                { label: "AI Responses Cached", value: cache.namespaces.generate_text, accent: "#7C3AED", bg: "#F5F3FF" },
                { label: "Searches Cached",    value: cache.namespaces.retrieval,      accent: "#059669", bg: "#ECFDF5" },
                { label: "Memory Used",        value: cache.memory.used_memory_human,  accent: "#0284C7", bg: "#F0F9FF" },
              ].map(({ label, value, accent, bg }) => (
                <div key={label} className="rounded-xl p-3 border border-[var(--border)]" style={{ background: bg }}>
                  <p className="font-display text-lg font-bold" style={{ color: accent }}>{value}</p>
                  <p className="text-[11px] text-[var(--text)] font-medium mt-0.5">{label}</p>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
