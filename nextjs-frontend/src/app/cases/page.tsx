"use client";
import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { FolderSearch, Search, FileText, AlertTriangle, TrendingUp, Cpu } from "lucide-react";
import TopBar from "@/components/layout/TopBar";
import { searchCases } from "@/lib/api";
import type { SimilarCase } from "@/types";
import { cn, scoreColor, scoreLabel, formatLatency } from "@/lib/utils";

const EXAMPLE_QUERIES = [
  "ADGM company with UBO disclosure violations",
  "Employment contract probation period non-compliance",
  "Articles of Association missing share capital clause",
  "Board resolution without proper quorum",
  "Fully compliant shareholder resolution",
];

function SimilarityBar({ score }: { score: number }) {
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-1.5 rounded-full bg-navy-700/60 overflow-hidden">
        <motion.div
          className="h-full rounded-full"
          initial={{ width: 0 }}
          animate={{ width: `${score * 100}%` }}
          transition={{ duration: 0.8, ease: "easeOut" }}
          style={{ background: `linear-gradient(90deg, #34d4a0, #20b88a)` }}
        />
      </div>
      <span className="text-xs font-medium text-jade-400 w-8 text-right">
        {(score * 100).toFixed(0)}%
      </span>
    </div>
  );
}

function CaseCard({ c: sc, index }: { c: SimilarCase; index: number }) {
  const color = scoreColor(sc.compliance_score);

  return (
    <motion.div
      initial={{ opacity: 0, y: 14 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.06 }}
      className="glass glass-hover rounded-2xl p-5 space-y-4"
    >
      {/* Header */}
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <h4 className="text-sm font-semibold text-white truncate">{sc.document_name}</h4>
          <span className="inline-block mt-1 text-[10px] px-2 py-0.5 rounded-md bg-navy-700/60 border border-white/6 text-slate-500 capitalize">
            {sc.document_type.replace(/_/g, " ")}
          </span>
        </div>

        {/* Score badge */}
        <div
          className="flex-shrink-0 w-14 h-14 rounded-xl flex flex-col items-center justify-center border"
          style={{ borderColor: `${color}30`, background: `${color}10` }}
        >
          <span className="text-lg font-bold leading-none" style={{ color }}>{sc.compliance_score}</span>
          <span className="text-[9px] text-slate-500 mt-0.5">/ 100</span>
        </div>
      </div>

      {/* Stats row */}
      <div className="flex items-center gap-4 text-xs">
        <span
          className="flex items-center gap-1 px-2 py-0.5 rounded-lg border font-medium"
          style={{ color, borderColor: `${color}25`, background: `${color}10` }}
        >
          {scoreLabel(sc.compliance_score)}
        </span>
        <span className="flex items-center gap-1 text-slate-500">
          <AlertTriangle size={10} className="text-crimson-400" />
          {sc.violation_count} violations
        </span>
      </div>

      {/* Summary */}
      {sc.summary && (
        <p className="text-xs text-slate-500 leading-relaxed line-clamp-2">{sc.summary}</p>
      )}

      {/* Similarity bar */}
      <div>
        <div className="flex items-center justify-between mb-1.5">
          <span className="text-[10px] text-slate-600 flex items-center gap-1">
            <TrendingUp size={9} /> Semantic similarity
          </span>
        </div>
        <SimilarityBar score={sc.similarity_score} />
      </div>
    </motion.div>
  );
}

export default function CasesPage() {
  const [query, setQuery] = useState("");
  const [topK, setTopK] = useState(5);
  const [loading, setLoading] = useState(false);
  const [cases, setCases] = useState<SimilarCase[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [latency, setLatency] = useState<number | null>(null);

  async function handleSearch(q?: string) {
    const searchQuery = (q ?? query).trim();
    if (!searchQuery || loading) return;
    setQuery(q ?? query);
    setError(null);
    setCases(null);
    setLoading(true);
    const t0 = Date.now();
    try {
      const r = await searchCases(searchQuery, topK);
      setCases(r.results);
      setLatency(Date.now() - t0);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Search failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex flex-col h-full overflow-hidden">
      <TopBar title="Similar Cases" subtitle="Semantic search across historical ADGM compliance reviews" />

      <div className="flex-1 overflow-y-auto px-6 py-6 space-y-5 page-enter">
        {/* Search panel */}
        <div className="glass rounded-2xl p-5 space-y-4">
          <div className="flex items-center gap-2">
            <FolderSearch size={16} className="text-pink-400" />
            <h3 className="text-sm font-semibold text-white">Case Search</h3>
          </div>

          <div className="flex gap-3">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500 w-4 h-4" />
              <input
                value={query}
                onChange={e => setQuery(e.target.value)}
                onKeyDown={e => e.key === "Enter" && handleSearch()}
                placeholder="Describe the scenario, document type, or violation…"
                className="w-full bg-navy-800/80 border border-white/8 rounded-xl pl-10 pr-4 py-2.5 text-sm text-white placeholder:text-slate-600 focus:outline-none focus:border-pink-400/40 transition-all"
              />
            </div>

            <select
              value={topK}
              onChange={e => setTopK(Number(e.target.value))}
              className="bg-navy-800/80 border border-white/8 rounded-xl px-3 py-2.5 text-sm text-slate-300 focus:outline-none w-16"
            >
              {[3, 5, 10].map(n => <option key={n} value={n} className="bg-navy-900">Top {n}</option>)}
            </select>

            <motion.button
              whileHover={{ scale: 1.03 }}
              whileTap={{ scale: 0.97 }}
              onClick={() => handleSearch()}
              disabled={!query.trim() || loading}
              className={cn(
                "flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-medium transition-all whitespace-nowrap",
                query.trim() && !loading
                  ? "bg-pink-500/15 border border-pink-400/25 text-pink-300 hover:bg-pink-500/25"
                  : "bg-navy-700/50 border border-white/5 text-slate-600 cursor-not-allowed"
              )}
            >
              {loading ? <Cpu size={14} className="animate-spin-slow" /> : <Search size={14} />}
              {loading ? "Searching…" : "Search"}
            </motion.button>
          </div>

          {/* Examples */}
          <div className="flex flex-wrap gap-1.5">
            {EXAMPLE_QUERIES.map(q => (
              <button
                key={q}
                onClick={() => handleSearch(q)}
                className="text-[10px] px-2.5 py-1 rounded-lg bg-navy-800/60 border border-white/5 text-slate-500 hover:text-slate-300 hover:border-white/12 transition-all"
              >
                {q}
              </button>
            ))}
          </div>
        </div>

        {error && (
          <div className="rounded-xl border border-crimson-500/30 bg-crimson-500/8 p-4 text-sm text-crimson-400">
            {error}
          </div>
        )}

        {/* Loading skeleton */}
        {loading && (
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
            {Array.from({ length: topK }).map((_, i) => (
              <div key={i} className="glass rounded-2xl p-5 space-y-3">
                <div className="flex gap-3">
                  <div className="flex-1 space-y-2">
                    <div className="h-4 rounded shimmer" />
                    <div className="h-3 w-24 rounded shimmer" />
                  </div>
                  <div className="w-14 h-14 rounded-xl shimmer" />
                </div>
                <div className="h-3 rounded shimmer" />
                <div className="h-3 w-3/4 rounded shimmer" />
                <div className="h-1.5 rounded shimmer" />
              </div>
            ))}
          </div>
        )}

        <AnimatePresence>
          {cases !== null && !loading && (
            <motion.div key="results" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2">
                  <FileText size={13} className="text-slate-500" />
                  <span className="text-sm text-slate-400">
                    <span className="font-semibold text-white">{cases.length}</span> cases found
                  </span>
                </div>
                {latency && (
                  <span className="text-xs text-slate-600">{formatLatency(latency)}</span>
                )}
              </div>

              {cases.length === 0 ? (
                <div className="glass rounded-2xl p-12 text-center">
                  <FolderSearch size={32} className="text-slate-600 mx-auto mb-3" />
                  <p className="text-sm text-slate-500">No similar cases found. Try a broader search query.</p>
                </div>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
                  {cases.map((c, i) => <CaseCard key={i} c={c} index={i} />)}
                </div>
              )}
            </motion.div>
          )}
        </AnimatePresence>

        {cases === null && !loading && !error && (
          <div className="flex flex-col items-center justify-center py-20 text-center space-y-4">
            <div className="w-16 h-16 rounded-2xl bg-pink-400/10 border border-pink-400/20 flex items-center justify-center animate-float">
              <FolderSearch size={26} className="text-pink-400" />
            </div>
            <div>
              <p className="text-sm font-medium text-white mb-1">Search Historical Cases</p>
              <p className="text-xs text-slate-500 max-w-sm">
                Find past ADGM compliance reviews similar to your scenario using semantic vector search.
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
