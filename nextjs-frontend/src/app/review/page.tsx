"use client";
import { useState, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useDropzone } from "react-dropzone";
import {
  Upload, FileText, AlertTriangle, CheckCircle2,
  ChevronDown, ChevronUp, Lightbulb, Users, Clock, Cpu,
} from "lucide-react";
import ReactMarkdown from "react-markdown";
import TopBar from "@/components/layout/TopBar";
import { reviewDocument } from "@/lib/api";
import type { ReviewReport, Violation, Recommendation, SimilarCase } from "@/types";
import { cn, scoreColor, scoreLabel, severityColor, priorityColor, formatLatency } from "@/lib/utils";

/* ── Score Gauge ─────────────────────────────────────────────────────────────── */
function ScoreGauge({ score }: { score: number }) {
  const radius = 52;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (score / 100) * circumference;
  const color = scoreColor(score);

  return (
    <div className="flex flex-col items-center justify-center">
      <svg width="140" height="140" className="-rotate-90">
        <circle cx="70" cy="70" r={radius} fill="none" stroke="rgba(255,255,255,0.06)" strokeWidth="10" />
        <motion.circle
          cx="70" cy="70" r={radius}
          fill="none"
          stroke={color}
          strokeWidth="10"
          strokeLinecap="round"
          strokeDasharray={circumference}
          initial={{ strokeDashoffset: circumference }}
          animate={{ strokeDashoffset: offset }}
          transition={{ duration: 1.2, ease: [0.4, 0, 0.2, 1], delay: 0.2 }}
          style={{ filter: `drop-shadow(0 0 8px ${color}60)` }}
        />
      </svg>
      <div className="absolute flex flex-col items-center">
        <motion.span
          className="text-3xl font-bold"
          style={{ color }}
          initial={{ opacity: 0, scale: 0.5 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: 0.5, duration: 0.4 }}
        >
          {score}
        </motion.span>
        <span className="text-xs text-slate-500 -mt-0.5">/ 100</span>
      </div>
    </div>
  );
}

/* ── Violation Card ──────────────────────────────────────────────────────────── */
function ViolationCard({ v, index }: { v: Violation; index: number }) {
  const [open, setOpen] = useState(index === 0);
  const c = severityColor(v.severity);

  return (
    <motion.div
      initial={{ opacity: 0, x: -12 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ delay: index * 0.05 }}
      className="rounded-xl border overflow-hidden"
      style={{ borderColor: c.border, background: c.bg }}
    >
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center justify-between px-4 py-3 text-left"
      >
        <div className="flex items-center gap-3">
          <AlertTriangle size={14} style={{ color: c.text }} className="flex-shrink-0" />
          <span className="text-sm font-medium text-white">{v.title}</span>
          <span
            className="px-2 py-0.5 rounded-md text-[10px] font-semibold uppercase tracking-wide"
            style={{ color: c.text, background: `${c.border}` }}
          >
            {v.severity}
          </span>
        </div>
        {open ? <ChevronUp size={14} className="text-slate-500" /> : <ChevronDown size={14} className="text-slate-500" />}
      </button>
      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="px-4 pb-3 space-y-2"
          >
            <p className="text-xs text-slate-400 leading-relaxed">{v.description}</p>
            {v.clause_reference && (
              <p className="text-xs text-slate-600">Clause: <span className="text-gold-400">{v.clause_reference}</span></p>
            )}
            {v.regulation_reference && (
              <p className="text-xs text-slate-600">Regulation: <span className="text-jade-400">{v.regulation_reference}</span></p>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}

/* ── Recommendation Card ─────────────────────────────────────────────────────── */
function RecommendationCard({ r, index }: { r: Recommendation; index: number }) {
  const c = priorityColor(r.priority);
  return (
    <motion.div
      initial={{ opacity: 0, x: -12 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ delay: index * 0.05 }}
      className="rounded-xl border p-4"
      style={{ borderColor: c.border, background: c.bg }}
    >
      <div className="flex items-start gap-3">
        <Lightbulb size={14} style={{ color: c.text }} className="flex-shrink-0 mt-0.5" />
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="text-sm font-medium text-white">{r.title}</span>
            <span className="px-1.5 py-0.5 rounded text-[10px] font-semibold uppercase"
              style={{ color: c.text, background: `${c.border}` }}>
              {r.priority}
            </span>
          </div>
          <p className="text-xs text-slate-400 leading-relaxed">{r.description}</p>
          {r.action_required && (
            <p className="text-xs text-gold-400 mt-1.5 font-medium">→ {r.action_required}</p>
          )}
        </div>
      </div>
    </motion.div>
  );
}

/* ── Similar Case Card ───────────────────────────────────────────────────────── */
function SimilarCaseCard({ c: sc }: { c: SimilarCase }) {
  const color = scoreColor(sc.compliance_score);
  return (
    <div className="glass glass-hover rounded-xl p-4">
      <div className="flex items-center justify-between mb-2">
        <span className="text-xs font-medium text-slate-300 truncate flex-1 mr-2">{sc.document_name}</span>
        <span className="text-sm font-bold flex-shrink-0" style={{ color }}>{sc.compliance_score}</span>
      </div>
      <div className="flex items-center gap-2 text-[10px] text-slate-600">
        <span className="px-1.5 py-0.5 rounded bg-navy-700/60 border border-white/5 text-slate-500">{sc.document_type}</span>
        <span>{sc.violation_count} violations</span>
        <span className="ml-auto text-jade-400">~{(sc.similarity_score * 100).toFixed(0)}% similar</span>
      </div>
    </div>
  );
}

/* ── Drop Zone ───────────────────────────────────────────────────────────────── */
function DropZone({ onFile, loading }: { onFile: (f: File) => void; loading: boolean }) {
  const onDrop = useCallback((files: File[]) => {
    if (files[0]) onFile(files[0]);
  }, [onFile]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { "application/pdf": [".pdf"], "application/vnd.openxmlformats-officedocument.wordprocessingml.document": [".docx"] },
    multiple: false,
    disabled: loading,
  });

  return (
    <div
      {...getRootProps()}
      className={cn(
        "relative border-2 border-dashed rounded-2xl p-12 text-center cursor-pointer transition-all duration-300",
        isDragActive
          ? "border-gold-400/60 bg-gold-400/5"
          : "border-white/10 hover:border-gold-400/30 hover:bg-white/2",
        loading && "opacity-50 cursor-not-allowed"
      )}
    >
      <input {...getInputProps()} />
      {/* Animated border glow on drag */}
      {isDragActive && (
        <div className="absolute inset-0 rounded-2xl animate-pulse-gold pointer-events-none" />
      )}
      <motion.div
        animate={isDragActive ? { scale: 1.1 } : { scale: 1 }}
        className="flex flex-col items-center gap-4"
      >
        <div className={cn(
          "w-16 h-16 rounded-2xl flex items-center justify-center transition-all",
          isDragActive ? "bg-gold-400/20 border border-gold-400/40" : "bg-navy-700/60 border border-white/8"
        )}>
          {loading ? (
            <Cpu size={24} className="text-jade-400 animate-spin-slow" />
          ) : (
            <Upload size={24} className={isDragActive ? "text-gold-400" : "text-slate-500"} />
          )}
        </div>
        <div>
          <p className="text-sm font-medium text-white">
            {loading ? "Analysing document…" : isDragActive ? "Drop to upload" : "Drop your document here"}
          </p>
          <p className="text-xs text-slate-500 mt-1">
            {loading ? "Running 6 specialist AI agents — this takes ~30 seconds" : "Supports PDF and DOCX · Max 50MB"}
          </p>
        </div>
        {!loading && (
          <span className="text-xs px-4 py-1.5 rounded-lg bg-navy-700/60 border border-white/8 text-slate-400">
            Or click to browse files
          </span>
        )}
      </motion.div>
    </div>
  );
}

/* ── Main page ───────────────────────────────────────────────────────────────── */
export default function ReviewPage() {
  const [loading, setLoading] = useState(false);
  const [report, setReport] = useState<ReviewReport | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<"violations" | "recommendations" | "cases">("violations");

  async function handleFile(file: File) {
    setError(null);
    setReport(null);
    setLoading(true);
    try {
      const r = await reviewDocument(file);
      setReport(r);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Review failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex flex-col h-full overflow-hidden">
      <TopBar title="Document Review" subtitle="6 AI agents · Violations · Gap Analysis · Compliance Score" />

      <div className="flex-1 overflow-y-auto px-6 py-6 space-y-6 page-enter">
        {!report && (
          <>
            <DropZone onFile={handleFile} loading={loading} />
            {error && (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="rounded-xl border border-crimson-500/30 bg-crimson-500/8 p-4 text-sm text-crimson-400"
              >
                {error}
              </motion.div>
            )}
          </>
        )}

        {report && (
          <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} className="space-y-5">
            {/* Header card */}
            <div className="glass rounded-2xl p-6">
              <div className="flex items-start gap-6 flex-wrap">
                {/* Score gauge */}
                <div className="relative flex items-center justify-center">
                  <ScoreGauge score={report.compliance_score} />
                </div>

                {/* Info */}
                <div className="flex-1 min-w-[200px] space-y-3">
                  <div>
                    <h2 className="text-lg font-semibold text-white">{report.document_name}</h2>
                    <div className="flex items-center gap-2 mt-1">
                      <FileText size={13} className="text-slate-500" />
                      <span className="text-xs text-slate-500 capitalize">{report.document_type.replace("_", " ")}</span>
                      <span className="text-slate-700">·</span>
                      <span className="text-xs font-semibold" style={{ color: scoreColor(report.compliance_score) }}>
                        {scoreLabel(report.compliance_score)}
                      </span>
                    </div>
                  </div>

                  <p className="text-xs text-slate-400 leading-relaxed">{report.summary}</p>

                  <div className="flex flex-wrap gap-3 text-xs text-slate-500">
                    <span className="flex items-center gap-1.5">
                      <AlertTriangle size={11} className="text-crimson-400" />
                      {report.violations.length} violations
                    </span>
                    <span className="flex items-center gap-1.5">
                      <Lightbulb size={11} className="text-gold-400" />
                      {report.recommendations.length} recommendations
                    </span>
                    <span className="flex items-center gap-1.5">
                      <Users size={11} className="text-jade-400" />
                      {report.similar_cases.length} similar cases
                    </span>
                    <span className="flex items-center gap-1.5">
                      <Clock size={11} />
                      {formatLatency(report.latency_ms)}
                    </span>
                  </div>
                </div>
              </div>
            </div>

            {/* Tabs */}
            <div className="flex items-center gap-1 bg-navy-800/50 rounded-xl p-1 border border-white/5 w-fit">
              {(["violations", "recommendations", "cases"] as const).map(tab => (
                <button
                  key={tab}
                  onClick={() => setActiveTab(tab)}
                  className={cn(
                    "px-4 py-1.5 rounded-lg text-xs font-medium transition-all capitalize",
                    activeTab === tab
                      ? "bg-gold-500/15 text-gold-400 border border-gold-500/20"
                      : "text-slate-500 hover:text-slate-300"
                  )}
                >
                  {tab === "violations" ? `Violations (${report.violations.length})` :
                   tab === "recommendations" ? `Recommendations (${report.recommendations.length})` :
                   `Similar Cases (${report.similar_cases.length})`}
                </button>
              ))}
            </div>

            {/* Tab content */}
            <AnimatePresence mode="wait">
              {activeTab === "violations" && (
                <motion.div key="v" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="space-y-2">
                  {report.violations.length === 0 ? (
                    <div className="glass rounded-xl p-8 text-center text-slate-500 text-sm">
                      <CheckCircle2 className="w-8 h-8 text-jade-400 mx-auto mb-2" />
                      No violations detected
                    </div>
                  ) : (
                    report.violations.map((v, i) => <ViolationCard key={i} v={v} index={i} />)
                  )}
                </motion.div>
              )}
              {activeTab === "recommendations" && (
                <motion.div key="r" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="space-y-2">
                  {report.recommendations.map((r, i) => <RecommendationCard key={i} r={r} index={i} />)}
                </motion.div>
              )}
              {activeTab === "cases" && (
                <motion.div key="c" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  {report.similar_cases.length === 0 ? (
                    <p className="text-sm text-slate-500 col-span-2">No similar historical cases found.</p>
                  ) : (
                    report.similar_cases.map((c, i) => <SimilarCaseCard key={i} c={c} />)
                  )}
                </motion.div>
              )}
            </AnimatePresence>

            <button
              onClick={() => { setReport(null); setError(null); }}
              className="text-xs text-slate-600 hover:text-slate-400 transition-colors"
            >
              ← Review another document
            </button>
          </motion.div>
        )}
      </div>
    </div>
  );
}
