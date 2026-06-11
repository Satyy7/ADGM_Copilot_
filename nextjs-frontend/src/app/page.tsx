"use client";
import { motion } from "framer-motion";
import Link from "next/link";
import {
  MessageSquare, FileSearch, Wand2, BarChart3,
  FolderSearch, TrendingUp, Shield, Zap,
  ArrowRight, Database, Clock,
} from "lucide-react";
import { useEffect, useState } from "react";
import TopBar from "@/components/layout/TopBar";
import { getCacheStats } from "@/lib/api";
import type { CacheStats } from "@/types";

const CAPABILITIES = [
  {
    href: "/chat",
    icon: MessageSquare,
    title: "Compliance Chat",
    description: "Ask any ADGM regulatory question and get precise, cited answers from the official knowledge base.",
    color: "#34d4a0",
    gradient: "from-jade-400/10 to-transparent",
    badge: "RAG · HyDE · CRAG · Self-RAG",
  },
  {
    href: "/review",
    icon: FileSearch,
    title: "Document Review",
    description: "Upload PDF or DOCX. Six specialist AI agents analyse for violations, gaps, and generate a compliance score.",
    color: "#7dd3fc",
    gradient: "from-blue-400/10 to-transparent",
    badge: "6 AI Agents · Score · Citations",
  },
  {
    href: "/clauses",
    icon: Wand2,
    title: "Clause Generator",
    description: "Draft ADGM-compliant legal clauses with precise article references, ready for Articles of Association or contracts.",
    color: "#c084fc",
    gradient: "from-purple-400/10 to-transparent",
    badge: "Template RAG · Cited",
  },
  {
    href: "/analytics",
    icon: BarChart3,
    title: "Analytics",
    description: "Ask data questions in plain English. The AI writes SQL, shows you a preview, and waits for your approval.",
    color: "#fb923c",
    gradient: "from-orange-400/10 to-transparent",
    badge: "Text2SQL · Human-in-Loop",
  },
  {
    href: "/cases",
    icon: FolderSearch,
    title: "Similar Cases",
    description: "Find historical compliance reviews matching your scenario. Semantic search across all past documents.",
    color: "#f472b6",
    gradient: "from-pink-400/10 to-transparent",
    badge: "Vector Search · Dense",
  },
];

const STATS = [
  { label: "Knowledge Chunks",   value: "12,500+", icon: Database,    color: "#d4a030" },
  { label: "Avg Compliance Score", value: "74/100", icon: Shield,     color: "#34d4a0" },
  { label: "Retrieval Stack",    value: "5-Layer",  icon: Zap,        color: "#c084fc" },
  { label: "Avg Latency",        value: "~8s",      icon: Clock,      color: "#7dd3fc" },
];

function StatCard({ label, value, icon: Icon, color, delay }: typeof STATS[0] & { delay: number }) {
  const [displayed, setDisplayed] = useState("—");
  useEffect(() => {
    const t = setTimeout(() => setDisplayed(value), delay * 100 + 300);
    return () => clearTimeout(t);
  }, [value, delay]);

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: delay * 0.1, duration: 0.4 }}
      className="glass glass-hover rounded-2xl p-5 flex items-center gap-4"
    >
      <div
        className="w-11 h-11 rounded-xl flex items-center justify-center flex-shrink-0"
        style={{ background: `${color}18`, border: `1px solid ${color}30` }}
      >
        <Icon size={20} style={{ color }} />
      </div>
      <div>
        <p className="text-xl font-bold text-white">{displayed}</p>
        <p className="text-xs text-slate-500 mt-0.5">{label}</p>
      </div>
    </motion.div>
  );
}

export default function DashboardPage() {
  const [cache, setCache] = useState<CacheStats | null>(null);

  useEffect(() => {
    getCacheStats().then(setCache).catch(() => null);
  }, []);

  return (
    <div className="flex flex-col h-full overflow-hidden">
      <TopBar title="Dashboard" subtitle="ADGM Compliance Intelligence Platform" />

      <div className="flex-1 overflow-y-auto px-6 py-6 space-y-8">
        {/* Hero */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          className="relative overflow-hidden rounded-2xl border border-gold-500/20 bg-gradient-to-br from-gold-500/8 via-navy-800/50 to-transparent p-8"
        >
          {/* Decorative glow */}
          <div className="absolute -top-20 -right-20 w-72 h-72 rounded-full bg-gold-500/5 blur-3xl pointer-events-none" />
          <div className="absolute -bottom-10 -left-10 w-48 h-48 rounded-full bg-jade-400/5 blur-3xl pointer-events-none" />

          <div className="relative flex items-start justify-between flex-wrap gap-4">
            <div>
              <div className="flex items-center gap-2 mb-3">
                <div className="status-dot" />
                <span className="text-xs text-slate-400 font-medium">All systems operational</span>
              </div>
              <h2 className="text-3xl font-bold text-white mb-2">
                Welcome to{" "}
                <span className="text-gold-gradient">ADGM Nexus</span>
              </h2>
              <p className="text-slate-400 text-sm max-w-lg leading-relaxed">
                Enterprise-grade AI compliance platform for the Abu Dhabi Global Market.
                16-phase intelligence stack — from hybrid retrieval to self-grading answers.
              </p>
              <div className="flex flex-wrap gap-2 mt-4">
                {["HyDE", "CRAG", "Self-RAG", "Redis Cache", "Text2SQL"].map(tag => (
                  <span key={tag} className="px-2.5 py-1 rounded-lg text-xs font-medium bg-navy-700/80 border border-white/8 text-slate-400">
                    {tag}
                  </span>
                ))}
              </div>
            </div>
            <Link href="/chat">
              <motion.button
                whileHover={{ scale: 1.03 }}
                whileTap={{ scale: 0.97 }}
                className="flex items-center gap-2 bg-gold-500 hover:bg-gold-400 text-navy-950 font-semibold text-sm px-5 py-2.5 rounded-xl transition-colors shadow-gold-sm"
              >
                Start Chatting <ArrowRight size={15} />
              </motion.button>
            </Link>
          </div>
        </motion.div>

        {/* Stats row */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          {STATS.map((s, i) => <StatCard key={s.label} {...s} delay={i} />)}
        </div>

        {/* Capabilities grid */}
        <div>
          <h3 className="text-sm font-semibold text-slate-400 mb-4 flex items-center gap-2">
            <TrendingUp size={14} /> Capabilities
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
            {CAPABILITIES.map(({ href, icon: Icon, title, description, color, gradient, badge }, i) => (
              <motion.div
                key={href}
                initial={{ opacity: 0, y: 16 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.15 + i * 0.07, duration: 0.35 }}
              >
                <Link href={href}>
                  <div className="glass glass-hover rounded-2xl p-5 h-full cursor-pointer group relative overflow-hidden">
                    {/* Color accent top */}
                    <div
                      className="absolute top-0 left-0 right-0 h-px opacity-60"
                      style={{ background: `linear-gradient(90deg, transparent, ${color}, transparent)` }}
                    />

                    <div className="flex items-start justify-between mb-3">
                      <div
                        className="w-10 h-10 rounded-xl flex items-center justify-center"
                        style={{ background: `${color}18`, border: `1px solid ${color}28` }}
                      >
                        <Icon size={18} style={{ color }} />
                      </div>
                      <ArrowRight
                        size={14}
                        className="text-slate-600 group-hover:text-slate-400 group-hover:translate-x-1 transition-all duration-200 mt-1"
                      />
                    </div>

                    <h4 className="text-sm font-semibold text-white mb-1.5 group-hover:text-gold-300 transition-colors">
                      {title}
                    </h4>
                    <p className="text-xs text-slate-500 leading-relaxed mb-3">{description}</p>
                    <span className="inline-block text-xs px-2 py-0.5 rounded-md bg-navy-700/60 border border-white/6 text-slate-500">
                      {badge}
                    </span>
                  </div>
                </Link>
              </motion.div>
            ))}
          </div>
        </div>

        {/* Cache stats */}
        {cache && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.6 }}
            className="glass rounded-2xl p-5"
          >
            <h3 className="text-sm font-semibold text-slate-400 mb-4 flex items-center gap-2">
              <Database size={14} /> Redis Cache Status
            </h3>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              {[
                { label: "Embeddings",    value: cache.namespaces.embeddings,    ttl: "7 days",   color: "#d4a030" },
                { label: "LLM Responses", value: cache.namespaces.generate_text,  ttl: "1 hour",   color: "#c084fc" },
                { label: "Retrieval",     value: cache.namespaces.retrieval,      ttl: "30 min",   color: "#34d4a0" },
                { label: "Total Keys",    value: cache.total_cached_keys,         ttl: cache.memory.used_memory_human, color: "#7dd3fc" },
              ].map(({ label, value, ttl, color }) => (
                <div key={label} className="rounded-xl bg-navy-800/50 border border-white/5 p-3">
                  <p className="text-lg font-bold" style={{ color }}>{value.toLocaleString()}</p>
                  <p className="text-xs text-slate-400 mt-0.5">{label}</p>
                  <p className="text-xs text-slate-600 mt-0.5">TTL: {ttl}</p>
                </div>
              ))}
            </div>
          </motion.div>
        )}
      </div>
    </div>
  );
}
