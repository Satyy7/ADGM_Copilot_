"use client";
import { useState } from "react";
import { Gavel, Search, FileText, AlertTriangle, TrendingUp, Loader2 } from "lucide-react";
import TopBar from "@/components/layout/TopBar";
import { searchCases } from "@/lib/api";
import type { SimilarCase } from "@/types";
import { scoreColor, scoreLabel, formatLatency } from "@/lib/utils";

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
      <div className="flex-1 h-1.5 rounded-full bg-[var(--border)] overflow-hidden">
        <div
          className="h-full rounded-full transition-all duration-700"
          style={{ width: `${score * 100}%`, background: "linear-gradient(90deg,#D97706,#B45309)" }}
        />
      </div>
      <span className="text-[10.5px] font-semibold text-amber-700 w-8 text-right">
        {(score * 100).toFixed(0)}%
      </span>
    </div>
  );
}

function CaseCard({ sc, index }: { sc: SimilarCase; index: number }) {
  const color = scoreColor(sc.compliance_score);
  return (
    <div className="card card-hover rounded-2xl p-5 space-y-3">
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <h4 className="font-display text-[13.5px] font-semibold text-[var(--text)] truncate">{sc.document_name}</h4>
          <span
            className="badge mt-1 text-[10px]"
            style={{ background: "#F0F9FF", borderColor: "#BAE6FD", color: "#0284C7" }}
          >
            {sc.document_type.replace(/_/g, " ")}
          </span>
        </div>
        <div
          className="flex-shrink-0 w-14 h-14 rounded-xl flex flex-col items-center justify-center border"
          style={{ borderColor: `${color}30`, background: `${color}10` }}
        >
          <span className="font-display text-lg font-bold leading-none" style={{ color }}>{sc.compliance_score}</span>
          <span className="text-[9px] text-[var(--text-3)] mt-0.5">/ 100</span>
        </div>
      </div>

      <div className="flex items-center gap-3 text-[11px]">
        <span
          className="badge text-[10px]"
          style={{ background: `${color}10`, borderColor: `${color}25`, color }}
        >
          {scoreLabel(sc.compliance_score)}
        </span>
        <span className="flex items-center gap-1 text-[var(--text-3)]">
          <AlertTriangle size={9} className="text-rose-500" /> {sc.violation_count} violations
        </span>
      </div>

      {sc.summary && (
        <p className="text-[12px] text-[var(--text-2)] leading-relaxed line-clamp-2">{sc.summary}</p>
      )}

      <div>
        <div className="flex items-center justify-between mb-1.5">
          <span className="text-[10px] text-[var(--text-3)] flex items-center gap-1">
            <TrendingUp size={9} /> Semantic similarity
          </span>
        </div>
        <SimilarityBar score={sc.similarity_score} />
      </div>
    </div>
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
    const sq = (q ?? query).trim();
    if (!sq || loading) return;
    if (q) setQuery(q);
    setError(null); setCases(null); setLoading(true);
    const t0 = Date.now();
    try {
      const r = await searchCases(sq, topK);
      setCases(r.results);
      setLatency(Date.now() - t0);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Search failed");
    } finally { setLoading(false); }
  }

  return (
    <div className="flex flex-col h-full overflow-hidden">
      <TopBar title="Case Search" subtitle="Find historical ADGM compliance reviews similar to your scenario" />

      <div className="flex-1 overflow-y-auto px-6 py-6 space-y-5 page-enter">
        {/* Search panel */}
        <div className="card p-5 space-y-4">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg flex items-center justify-center" style={{ background: "#FDF2F8", border: "1.5px solid #FBCFE8" }}>
              <Gavel size={14} className="text-pink-600" />
            </div>
            <h3 className="font-display text-sm font-semibold text-[var(--text)]">Case Search</h3>
          </div>

          <div className="flex gap-3">
            <div className="relative flex-1 min-w-0">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--text-3)] w-4 h-4 z-10" />
              <input
                value={query}
                onChange={e => setQuery(e.target.value)}
                onKeyDown={e => e.key === "Enter" && handleSearch()}
                placeholder="Describe the scenario, document type, or violation…"
                className="w-full bg-[var(--surface-alt)] border border-[var(--border)] rounded-xl pl-10 pr-4 py-2.5 text-sm text-[var(--text)] placeholder:text-[var(--text-3)] focus:outline-none focus:border-amber-300 focus:bg-white transition-all"
              />
            </div>

            <select
              value={topK}
              onChange={e => setTopK(Number(e.target.value))}
              className="flex-shrink-0 w-24 bg-[var(--surface-alt)] border border-[var(--border)] rounded-xl px-3 py-2.5 text-sm text-[var(--text)] focus:outline-none focus:border-amber-300 cursor-pointer"
            >
              {[3, 5, 10].map(n => <option key={n} value={n}>Top {n}</option>)}
            </select>

            <button
              onClick={() => handleSearch()}
              disabled={!query.trim() || loading}
              className="flex items-center gap-2 px-5 py-2 rounded-xl text-sm font-medium transition-all whitespace-nowrap border"
              style={
                query.trim() && !loading
                  ? { background: "#FDF2F8", borderColor: "#FBCFE8", color: "#DB2777" }
                  : { background: "var(--surface-alt)", borderColor: "var(--border)", color: "var(--text-3)", cursor: "not-allowed" }
              }
            >
              {loading ? <Loader2 size={13} className="animate-spin" /> : <Search size={13} />}
              {loading ? "Searching…" : "Search"}
            </button>
          </div>

          <div className="flex flex-wrap gap-1.5">
            {EXAMPLE_QUERIES.map(q => (
              <button
                key={q}
                onClick={() => handleSearch(q)}
                className="text-[10.5px] px-2.5 py-1 rounded-lg bg-[var(--surface-alt)] border border-[var(--border)] text-[var(--text-3)] hover:text-pink-700 hover:border-pink-200 hover:bg-pink-50 transition-all"
              >
                {q}
              </button>
            ))}
          </div>
        </div>

        {error && (
          <div className="card rounded-xl p-4 border-rose-200 text-sm text-rose-700" style={{ background: "#FFF1F2" }}>
            {error}
          </div>
        )}

        {/* Skeleton */}
        {loading && (
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
            {Array.from({ length: topK }).map((_, i) => (
              <div key={i} className="card rounded-2xl p-5 space-y-3">
                <div className="flex gap-3">
                  <div className="flex-1 space-y-2">
                    <div className="h-4 rounded-lg shimmer" />
                    <div className="h-3 w-24 rounded-lg shimmer" />
                  </div>
                  <div className="w-14 h-14 rounded-xl shimmer" />
                </div>
                <div className="h-3 rounded-lg shimmer" />
                <div className="h-3 w-3/4 rounded-lg shimmer" />
                <div className="h-1.5 rounded-full shimmer" />
              </div>
            ))}
          </div>
        )}

        {cases !== null && !loading && (
          <div>
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2">
                <FileText size={13} className="text-[var(--text-3)]" />
                <span className="text-sm text-[var(--text-2)]">
                  <span className="font-semibold text-[var(--text)]">{cases.length}</span> cases found
                </span>
              </div>
              {latency && <span className="text-[11px] text-[var(--text-3)]">{formatLatency(latency)}</span>}
            </div>

            {cases.length === 0 ? (
              <div className="card rounded-2xl p-12 text-center">
                <Gavel size={32} className="text-[var(--text-3)] mx-auto mb-3" />
                <p className="text-sm text-[var(--text-3)]">No similar cases found. Try a broader search query.</p>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
                {cases.map((c, i) => <CaseCard key={i} sc={c} index={i} />)}
              </div>
            )}
          </div>
        )}

        {cases === null && !loading && !error && (
          <div className="flex flex-col items-center justify-center py-20 text-center space-y-4">
            <div
              className="w-16 h-16 rounded-2xl flex items-center justify-center"
              style={{ background: "#FDF2F8", border: "1.5px solid #FBCFE8" }}
            >
              <Gavel size={26} className="text-pink-500" />
            </div>
            <div>
              <p className="font-display text-base font-semibold text-[var(--text)] mb-1">Search Historical Cases</p>
              <p className="text-sm text-[var(--text-2)] max-w-sm">
                Find past ADGM compliance reviews similar to your scenario using semantic vector search.
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
