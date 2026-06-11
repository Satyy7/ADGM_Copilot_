"use client";
import { useState, useCallback } from "react";
import { useDropzone } from "react-dropzone";
import {
  Upload, FileText, AlertTriangle, CheckCircle2,
  ChevronDown, ChevronUp, Lightbulb, Users, Clock, Loader2,
} from "lucide-react";
import ReactMarkdown from "react-markdown";
import TopBar from "@/components/layout/TopBar";
import { reviewDocument } from "@/lib/api";
import type { ReviewReport, Violation, Recommendation, SimilarCase } from "@/types";
import { scoreColor, scoreLabel, severityColor, priorityColor, formatLatency } from "@/lib/utils";

/* ── Score Ring ──────────────────────────────────────────────────────────────── */
function ScoreRing({ score }: { score: number }) {
  const r = 46, c = 2 * Math.PI * r;
  const color = scoreColor(score);
  const fill = c - (score / 100) * c;
  return (
    <div className="relative flex items-center justify-center w-32 h-32 flex-shrink-0">
      <svg width="128" height="128" className="-rotate-90" style={{ position: "absolute" }}>
        <circle cx="64" cy="64" r={r} fill="none" stroke="#EDE9DF" strokeWidth="9" />
        <circle
          cx="64" cy="64" r={r} fill="none"
          stroke={color} strokeWidth="9" strokeLinecap="round"
          strokeDasharray={c} strokeDashoffset={fill}
          style={{ transition: "stroke-dashoffset 1.2s cubic-bezier(.4,0,.2,1)" }}
        />
      </svg>
      <div className="flex flex-col items-center z-10">
        <span className="font-display text-3xl font-bold" style={{ color }}>{score}</span>
        <span className="text-[10px] text-[var(--text-3)]">/ 100</span>
      </div>
    </div>
  );
}

/* ── Violation ───────────────────────────────────────────────────────────────── */
function ViolationCard({ v, index }: { v: Violation; index: number }) {
  const [open, setOpen] = useState(index === 0);
  const c = severityColor(v.severity);
  return (
    <div className="card rounded-xl overflow-hidden" style={{ borderColor: c.border }}>
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center justify-between px-4 py-3 text-left"
        style={{ background: c.bg }}
      >
        <div className="flex items-center gap-3 min-w-0">
          <AlertTriangle size={13} style={{ color: c.text }} className="flex-shrink-0" />
          <span className="text-sm font-medium text-[var(--text)] truncate">{v.title}</span>
          <span className="badge text-[10px] flex-shrink-0" style={{ background: c.bg, borderColor: c.border, color: c.text }}>
            {v.severity}
          </span>
        </div>
        {open ? <ChevronUp size={13} className="text-[var(--text-3)] flex-shrink-0 ml-2" /> : <ChevronDown size={13} className="text-[var(--text-3)] flex-shrink-0 ml-2" />}
      </button>
      {open && (
        <div className="px-4 pb-3 pt-2 space-y-1.5 bg-white">
          <p className="text-[12.5px] text-[var(--text-2)] leading-relaxed">{v.description}</p>
          {v.clause_reference && (
            <p className="text-xs text-[var(--text-3)]">Clause: <span className="text-amber-700 font-medium">{v.clause_reference}</span></p>
          )}
          {v.regulation_reference && (
            <p className="text-xs text-[var(--text-3)]">Regulation: <span className="text-sky-700 font-medium">{v.regulation_reference}</span></p>
          )}
        </div>
      )}
    </div>
  );
}

/* ── Recommendation ──────────────────────────────────────────────────────────── */
function RecommendationCard({ r, index }: { r: Recommendation; index: number }) {
  const c = priorityColor(r.priority);
  return (
    <div className="card rounded-xl p-4" style={{ borderColor: c.border, background: c.bg }}>
      <div className="flex items-start gap-3">
        <Lightbulb size={13} style={{ color: c.text }} className="flex-shrink-0 mt-0.5" />
        <div>
          <div className="flex items-center gap-2 mb-1 flex-wrap">
            <span className="text-sm font-medium text-[var(--text)]">{r.title}</span>
            <span className="badge text-[10px]" style={{ background: c.bg, borderColor: c.border, color: c.text }}>{r.priority}</span>
          </div>
          <p className="text-[12.5px] text-[var(--text-2)] leading-relaxed">{r.description}</p>
          {r.action_required && (
            <p className="text-xs text-amber-700 mt-1.5 font-medium">→ {r.action_required}</p>
          )}
        </div>
      </div>
    </div>
  );
}

/* ── Similar Case ────────────────────────────────────────────────────────────── */
function SimilarCaseCard({ sc }: { sc: SimilarCase }) {
  const color = scoreColor(sc.compliance_score);
  return (
    <div className="card card-hover rounded-xl p-4">
      <div className="flex items-center justify-between mb-2">
        <span className="text-[12.5px] font-medium text-[var(--text)] truncate flex-1 mr-2">{sc.document_name}</span>
        <span className="font-display text-base font-bold flex-shrink-0" style={{ color }}>{sc.compliance_score}</span>
      </div>
      <div className="flex items-center gap-2 text-[10.5px] text-[var(--text-3)]">
        <span className="badge" style={{ background: "#F0F9FF", borderColor: "#BAE6FD", color: "#0284C7" }}>{sc.document_type}</span>
        <span>{sc.violation_count} violations</span>
        <span className="ml-auto text-jade-600 font-medium">~{(sc.similarity_score * 100).toFixed(0)}% similar</span>
      </div>
    </div>
  );
}

/* ── Drop Zone ───────────────────────────────────────────────────────────────── */
function DropZone({ onFile, loading }: { onFile: (f: File) => void; loading: boolean }) {
  const onDrop = useCallback((files: File[]) => { if (files[0]) onFile(files[0]); }, [onFile]);
  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { "application/pdf": [".pdf"], "application/vnd.openxmlformats-officedocument.wordprocessingml.document": [".docx"] },
    multiple: false,
    disabled: loading,
  });

  return (
    <div
      {...getRootProps()}
      className={`relative border-2 border-dashed rounded-2xl p-12 text-center cursor-pointer transition-all duration-200 ${
        isDragActive ? "border-amber-400 bg-amber-50" : "border-[var(--border-strong)] hover:border-amber-300 hover:bg-amber-50/30"
      } ${loading ? "opacity-50 cursor-not-allowed" : ""}`}
    >
      <input {...getInputProps()} />
      <div className="flex flex-col items-center gap-4">
        <div className={`w-16 h-16 rounded-2xl flex items-center justify-center ${isDragActive ? "bg-amber-100 border-2 border-amber-300" : "bg-[var(--surface-alt)] border border-[var(--border)]"}`}>
          {loading ? (
            <Loader2 size={24} className="text-amber-600 animate-spin" />
          ) : (
            <Upload size={24} className={isDragActive ? "text-amber-600" : "text-[var(--text-3)]"} />
          )}
        </div>
        <div>
          <p className="font-display text-base font-semibold text-[var(--text)] mb-1">
            {loading ? "Analysing document…" : isDragActive ? "Drop to upload" : "Drop your document here"}
          </p>
          <p className="text-sm text-[var(--text-3)]">
            {loading ? "Analysing document — this may take ~30 seconds" : "PDF or DOCX · Max 50 MB"}
          </p>
        </div>
        {!loading && (
          <span className="btn-outline text-xs py-1.5 px-4 pointer-events-none">Browse files</span>
        )}
      </div>
    </div>
  );
}

/* ── Main ────────────────────────────────────────────────────────────────────── */
export default function ReviewPage() {
  const [loading, setLoading] = useState(false);
  const [report, setReport] = useState<ReviewReport | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [tab, setTab] = useState<"violations" | "recommendations" | "cases">("violations");

  async function handleFile(file: File) {
    setError(null); setReport(null); setLoading(true);
    try { setReport(await reviewDocument(file)); }
    catch (e: unknown) { setError(e instanceof Error ? e.message : "Review failed"); }
    finally { setLoading(false); }
  }

  const violations      = report?.violations      ?? [];
  const recommendations = report?.recommendations ?? [];
  const similarCases    = report?.similar_cases   ?? [];

  const TABS = [
    { key: "violations",      label: `Violations (${violations.length})` },
    { key: "recommendations", label: `Recommendations (${recommendations.length})` },
    { key: "cases",           label: `Similar Cases (${similarCases.length})` },
  ] as const;

  return (
    <div className="flex flex-col h-full overflow-hidden">
      <TopBar title="Document Review" subtitle="Upload a document to get a full compliance analysis and score" />

      <div className="flex-1 overflow-y-auto px-6 py-6 space-y-6 page-enter">
        {!report && (
          <>
            <DropZone onFile={handleFile} loading={loading} />
            {error && (
              <div className="card rounded-xl p-4 border-rose-200 text-sm text-rose-700" style={{ background: "#FFF1F2" }}>
                {error}
              </div>
            )}
          </>
        )}

        {report && (
          <div className="space-y-5">
            {/* Header */}
            <div className="card p-6">
              <div className="flex items-start gap-6 flex-wrap">
                <ScoreRing score={report.compliance_score} />
                <div className="flex-1 min-w-[200px] space-y-3">
                  <div>
                    <h2 className="font-display text-lg font-semibold text-[var(--text)]">{report.document_name}</h2>
                    <div className="flex items-center gap-2 mt-1 flex-wrap">
                      <FileText size={12} className="text-[var(--text-3)]" />
                      <span className="text-[11px] text-[var(--text-3)] capitalize">{report.document_type.replace("_", " ")}</span>
                      <span className="text-[var(--border-strong)]">·</span>
                      <span className="text-[11px] font-semibold" style={{ color: scoreColor(report.compliance_score) }}>
                        {scoreLabel(report.compliance_score)}
                      </span>
                    </div>
                  </div>
                  <p className="text-[12.5px] text-[var(--text-2)] leading-relaxed">{report.summary}</p>
                  <div className="flex flex-wrap gap-3 text-[11px] text-[var(--text-3)]">
                    <span className="flex items-center gap-1"><AlertTriangle size={10} className="text-rose-500" />{violations.length} violations</span>
                    <span className="flex items-center gap-1"><Lightbulb size={10} className="text-amber-500" />{recommendations.length} recommendations</span>
                    <span className="flex items-center gap-1"><Users size={10} className="text-sky-500" />{similarCases.length} similar cases</span>
                    <span className="flex items-center gap-1"><Clock size={10} />{formatLatency(report.latency_ms)}</span>
                  </div>
                </div>
              </div>
            </div>

            {/* Tabs */}
            <div className="flex items-center gap-1 bg-[var(--surface-alt)] rounded-xl p-1 border border-[var(--border)] w-fit">
              {TABS.map(t => (
                <button
                  key={t.key}
                  onClick={() => setTab(t.key)}
                  className={`px-4 py-1.5 rounded-lg text-xs font-medium transition-all ${tab === t.key ? "tab-active" : "tab-inactive"}`}
                >
                  {t.label}
                </button>
              ))}
            </div>

            {/* Tab content */}
            {tab === "violations" && (
              <div className="space-y-2">
                {violations.length === 0 ? (
                  <div className="card rounded-xl p-8 text-center text-[var(--text-3)] text-sm">
                    <CheckCircle2 className="w-8 h-8 text-jade-600 mx-auto mb-2" /> No violations detected
                  </div>
                ) : violations.map((v, i) => <ViolationCard key={i} v={v} index={i} />)}
              </div>
            )}
            {tab === "recommendations" && (
              <div className="space-y-2">
                {recommendations.length === 0 ? (
                  <div className="card rounded-xl p-8 text-center text-[var(--text-3)] text-sm">
                    <CheckCircle2 className="w-8 h-8 text-jade-600 mx-auto mb-2" /> No recommendations
                  </div>
                ) : recommendations.map((r, i) => <RecommendationCard key={i} r={r} index={i} />)}
              </div>
            )}
            {tab === "cases" && (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {similarCases.length === 0
                  ? <p className="text-sm text-[var(--text-3)] col-span-2">No similar historical cases found.</p>
                  : similarCases.map((sc, i) => <SimilarCaseCard key={i} sc={sc} />)
                }
              </div>
            )}

            <button
              onClick={() => { setReport(null); setError(null); }}
              className="text-xs text-[var(--text-3)] hover:text-amber-600 transition-colors"
            >
              ← Review another document
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
