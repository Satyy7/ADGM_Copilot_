"use client";
import { useState } from "react";
import {
  Gavel, Search, FileText, AlertTriangle, TrendingUp,
  Loader2, X, BookOpen, ShieldAlert, Layers, Info,
} from "lucide-react";
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

// ── Similarity bar ─────────────────────────────────────────────────────────────

function SimilarityBar({ score }: { score: number }) {
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-1.5 rounded-full bg-[var(--border)] overflow-hidden">
        <div
          className="h-full rounded-full transition-all duration-700"
          style={{
            width: `${score * 100}%`,
            background: "linear-gradient(90deg,#D97706,#B45309)",
          }}
        />
      </div>
      <span className="text-[10.5px] font-semibold text-amber-700 w-8 text-right">
        {(score * 100).toFixed(0)}%
      </span>
    </div>
  );
}

// ── Case detail modal ──────────────────────────────────────────────────────────

function CaseDetailModal({ sc, onClose }: { sc: SimilarCase; onClose: () => void }) {
  const color = scoreColor(sc.compliance_score);

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      style={{ background: "rgba(0,0,0,0.45)" }}
      onClick={e => { if (e.target === e.currentTarget) onClose(); }}
    >
      <div className="bg-[var(--surface)] rounded-2xl shadow-2xl w-full max-w-xl max-h-[88vh] overflow-y-auto relative">

        {/* Close */}
        <button
          onClick={onClose}
          className="absolute top-4 right-4 w-8 h-8 flex items-center justify-center rounded-full bg-[var(--surface-alt)] hover:bg-[var(--border)] transition-colors z-10"
          aria-label="Close"
        >
          <X size={14} className="text-[var(--text-2)]" />
        </button>

        {/* Header */}
        <div className="p-6 border-b border-[var(--border)]">
          <div className="flex items-start gap-4 pr-8">
            <div
              className="flex-shrink-0 w-16 h-16 rounded-xl flex flex-col items-center justify-center border"
              style={{ borderColor: `${color}30`, background: `${color}10` }}
            >
              <span className="font-display text-xl font-bold leading-none" style={{ color }}>
                {sc.compliance_score}
              </span>
              <span className="text-[9px] text-[var(--text-3)] mt-0.5">/ 100</span>
            </div>
            <div className="flex-1 min-w-0">
              <h3 className="font-display text-base font-semibold text-[var(--text)] break-words leading-snug">
                {sc.document_name}
              </h3>
              <div className="flex items-center gap-2 mt-2 flex-wrap">
                <span
                  className="badge text-[10px]"
                  style={{ background: "#F0F9FF", borderColor: "#BAE6FD", color: "#0284C7" }}
                >
                  {sc.document_type.replace(/_/g, " ")}
                </span>
                <span
                  className="badge text-[10px]"
                  style={{ background: `${color}10`, borderColor: `${color}25`, color }}
                >
                  {scoreLabel(sc.compliance_score)}
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Body */}
        <div className="p-6 space-y-5">

          {/* Similarity score */}
          <div>
            <div className="flex items-center gap-1.5 mb-2">
              <TrendingUp size={12} className="text-amber-600" />
              <span className="text-xs font-semibold text-[var(--text-2)]">
                Semantic Similarity to Your Query
              </span>
            </div>
            <SimilarityBar score={sc.similarity_score} />
            <p className="text-[10.5px] text-[var(--text-3)] mt-1.5">
              Cosine similarity between your search query embedding and this indexed case.
            </p>
          </div>

          {/* Summary */}
          {sc.summary && (
            <div>
              <div className="flex items-center gap-1.5 mb-2">
                <BookOpen size={12} className="text-indigo-500" />
                <span className="text-xs font-semibold text-[var(--text-2)]">Review Summary</span>
              </div>
              <p className="text-sm text-[var(--text-2)] leading-relaxed">{sc.summary}</p>
            </div>
          )}

          {/* Stats row */}
          <div className="grid grid-cols-2 gap-3">
            <div
              className="rounded-xl p-3 space-y-1"
              style={{ background: "var(--surface-alt)", border: "1px solid var(--border)" }}
            >
              <div className="flex items-center gap-1.5">
                <AlertTriangle size={11} className="text-rose-500" />
                <span className="text-[11px] font-semibold text-[var(--text-2)]">Violations</span>
              </div>
              <p className="text-2xl font-display font-bold text-rose-600">{sc.violation_count}</p>
            </div>
            <div
              className="rounded-xl p-3 space-y-1"
              style={{ background: "var(--surface-alt)", border: "1px solid var(--border)" }}
            >
              <div className="flex items-center gap-1.5">
                <Layers size={11} className="text-orange-500" />
                <span className="text-[11px] font-semibold text-[var(--text-2)]">Missing Provisions</span>
              </div>
              <p className="text-2xl font-display font-bold text-orange-600">{sc.gap_count}</p>
            </div>
          </div>

          {/* Violation types */}
          {sc.violation_types && sc.violation_types.length > 0 && (
            <div>
              <div className="flex items-center gap-1.5 mb-2">
                <ShieldAlert size={12} className="text-rose-500" />
                <span className="text-xs font-semibold text-[var(--text-2)]">Violation Types</span>
              </div>
              <div className="flex flex-wrap gap-1.5">
                {sc.violation_types.map(vt => (
                  <span
                    key={vt}
                    className="text-[10.5px] px-2.5 py-1 rounded-lg border"
                    style={{ background: "#FFF1F2", borderColor: "#FECDD3", color: "#E11D48" }}
                  >
                    {vt.replace(/_/g, " ")}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Regulation references */}
          {sc.regulation_references && sc.regulation_references.length > 0 && (
            <div>
              <div className="flex items-center gap-1.5 mb-2">
                <Gavel size={12} className="text-indigo-500" />
                <span className="text-xs font-semibold text-[var(--text-2)]">ADGM Regulation References</span>
              </div>
              <div className="flex flex-wrap gap-1.5">
                {sc.regulation_references.map(rr => (
                  <span
                    key={rr}
                    className="text-[10.5px] px-2.5 py-1 rounded-lg border"
                    style={{ background: "#EEF2FF", borderColor: "#C7D2FE", color: "#4338CA" }}
                  >
                    {rr}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Fallback when no detail data captured */}
          {(!sc.violation_types || sc.violation_types.length === 0) &&
           (!sc.regulation_references || sc.regulation_references.length === 0) && (
            <div
              className="rounded-xl p-3 flex items-center gap-2"
              style={{ background: "var(--surface-alt)", border: "1px solid var(--border)" }}
            >
              <Info size={12} className="text-[var(--text-3)] flex-shrink-0" />
              <p className="text-[11px] text-[var(--text-3)]">
                Detailed violation and regulation data was not captured for this case.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// ── Case card ──────────────────────────────────────────────────────────────────

function CaseCard({ sc, onClick }: { sc: SimilarCase; onClick: () => void }) {
  const color = scoreColor(sc.compliance_score);
  return (
    <div
      className="card card-hover rounded-2xl p-5 space-y-3 cursor-pointer"
      onClick={onClick}
      role="button"
      tabIndex={0}
      onKeyDown={e => { if (e.key === "Enter" || e.key === " ") onClick(); }}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <h4 className="font-display text-[13.5px] font-semibold text-[var(--text)] truncate">
            {sc.document_name}
          </h4>
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
          <span className="font-display text-lg font-bold leading-none" style={{ color }}>
            {sc.compliance_score}
          </span>
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
          <AlertTriangle size={9} className="text-rose-500" /> {sc.violation_count} violation
          {sc.violation_count !== 1 ? "s" : ""}
        </span>
        {sc.gap_count > 0 && (
          <span className="flex items-center gap-1 text-[var(--text-3)]">
            <Layers size={9} className="text-orange-400" /> {sc.gap_count} gap
            {sc.gap_count !== 1 ? "s" : ""}
          </span>
        )}
      </div>

      {sc.summary && (
        <p className="text-[12px] text-[var(--text-2)] leading-relaxed line-clamp-2">{sc.summary}</p>
      )}

      <div>
        <div className="flex items-center justify-between mb-1.5">
          <span className="text-[10px] text-[var(--text-3)] flex items-center gap-1">
            <TrendingUp size={9} /> Semantic similarity
          </span>
          <span className="text-[10px] text-[var(--text-3)] underline decoration-dotted">
            Click for details
          </span>
        </div>
        <SimilarityBar score={sc.similarity_score} />
      </div>
    </div>
  );
}

// ── Page ───────────────────────────────────────────────────────────────────────

export default function CasesPage() {
  const [query, setQuery] = useState("");
  const [topK, setTopK] = useState(5);
  const [loading, setLoading] = useState(false);
  const [cases, setCases] = useState<SimilarCase[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [latency, setLatency] = useState<number | null>(null);
  const [selectedCase, setSelectedCase] = useState<SimilarCase | null>(null);

  async function handleSearch(q?: string) {
    const sq = (q ?? query).trim();
    if (!sq || loading) return;
    if (q) setQuery(q);
    setError(null);
    setCases(null);
    setLoading(true);
    const t0 = Date.now();
    try {
      const r = await searchCases(sq, topK);
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
      <TopBar
        title="Case Search"
        subtitle="Find historical ADGM compliance reviews similar to your scenario"
      />

      <div className="flex-1 overflow-y-auto px-6 py-6 space-y-5 page-enter">

        {/* Search panel */}
        <div className="card p-5 space-y-4">
          <div className="flex items-center gap-2">
            <div
              className="w-8 h-8 rounded-lg flex items-center justify-center"
              style={{ background: "#FDF2F8", border: "1.5px solid #FBCFE8" }}
            >
              <Gavel size={14} className="text-pink-600" />
            </div>
            <h3 className="font-display text-sm font-semibold text-[var(--text)]">
              Semantic Case Search
            </h3>
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
              {[3, 5, 10].map(n => (
                <option key={n} value={n}>Top {n}</option>
              ))}
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

        {/* Error */}
        {error && (
          <div
            className="card rounded-xl p-4 border-rose-200 text-sm text-rose-700"
            style={{ background: "#FFF1F2" }}
          >
            {error}
          </div>
        )}

        {/* Loading skeleton */}
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

        {/* Results */}
        {cases !== null && !loading && (
          <div>
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2">
                <FileText size={13} className="text-[var(--text-3)]" />
                <span className="text-sm text-[var(--text-2)]">
                  <span className="font-semibold text-[var(--text)]">{cases.length}</span>{" "}
                  case{cases.length !== 1 ? "s" : ""} found
                </span>
              </div>
              {latency != null && (
                <span className="text-[11px] text-[var(--text-3)]">{formatLatency(latency)}</span>
              )}
            </div>

            {cases.length === 0 ? (
              <div className="card rounded-2xl p-12 text-center space-y-3">
                <Gavel size={32} className="text-[var(--text-3)] mx-auto" />
                <p className="text-sm font-semibold text-[var(--text-2)]">No matching cases found</p>
                <p className="text-[12px] text-[var(--text-3)] max-w-sm mx-auto leading-relaxed">
                  Try a broader query, or run more document reviews — each completed review is
                  automatically indexed here for future similarity searches.
                </p>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
                {cases.map((c, i) => (
                  <CaseCard key={i} sc={c} onClick={() => setSelectedCase(c)} />
                ))}
              </div>
            )}
          </div>
        )}

        {/* Initial landing state */}
        {cases === null && !loading && !error && (
          <div className="flex flex-col items-center justify-center py-16 text-center space-y-6">
            <div
              className="w-16 h-16 rounded-2xl flex items-center justify-center"
              style={{ background: "#FDF2F8", border: "1.5px solid #FBCFE8" }}
            >
              <Gavel size={26} className="text-pink-500" />
            </div>
            <div>
              <p className="font-display text-base font-semibold text-[var(--text)] mb-2">
                Search Historical Compliance Cases
              </p>
              <p className="text-sm text-[var(--text-2)] max-w-md leading-relaxed">
                Every document you review via the{" "}
                <span className="font-medium text-[var(--text)]">Document Review</span> tab is
                automatically indexed here. Search by scenario, violation type, or document type to
                find past reviews with similar compliance patterns.
              </p>
            </div>
            <div className="grid grid-cols-3 gap-3 max-w-md w-full">
              {[
                {
                  icon: <Search size={14} className="text-pink-500" />,
                  label: "Semantic search",
                  sub: "Natural language queries",
                },
                {
                  icon: <TrendingUp size={14} className="text-amber-500" />,
                  label: "Similarity scores",
                  sub: "Vector cosine distance",
                },
                {
                  icon: <ShieldAlert size={14} className="text-indigo-500" />,
                  label: "Full case detail",
                  sub: "Violations & regulations",
                },
              ].map(item => (
                <div
                  key={item.label}
                  className="rounded-xl p-3 text-center space-y-1.5"
                  style={{ background: "var(--surface-alt)", border: "1px solid var(--border)" }}
                >
                  <div className="flex justify-center">{item.icon}</div>
                  <p className="text-[11px] font-semibold text-[var(--text-2)]">{item.label}</p>
                  <p className="text-[10px] text-[var(--text-3)]">{item.sub}</p>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Detail modal */}
      {selectedCase && (
        <CaseDetailModal sc={selectedCase} onClose={() => setSelectedCase(null)} />
      )}
    </div>
  );
}
