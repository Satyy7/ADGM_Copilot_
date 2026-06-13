"use client";
import { useState } from "react";
import { FileText, Copy, Check, BookOpen, Clock, Loader2, ChevronDown, Sparkles } from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import TopBar from "@/components/layout/TopBar";
import { generateClause } from "@/lib/api";
import type { ClauseResult } from "@/types";
import { formatLatency, collectionBadgeColor } from "@/lib/utils";
import { preprocessCitations, citationMarkdownComponents } from "@/components/CitationText";

const DOC_TYPES = [
  { value: "articles_of_association",  label: "Articles of Association" },
  { value: "memorandum_of_association",label: "Memorandum of Association" },
  { value: "employment_contract",       label: "Employment Contract" },
  { value: "board_resolution",          label: "Board Resolution" },
  { value: "shareholder_resolution",    label: "Shareholder Resolution" },
  { value: "ubo_declaration",           label: "UBO Declaration" },
  { value: "",                          label: "General / Other" },
];

const EXAMPLES = [
  "Draft a beneficial ownership (UBO) disclosure clause for Articles of Association of an ADGM company.",
  "Write a probation period clause compliant with ADGM Employment Regulations 2019.",
  "Draft a directors' authority clause for an ADGM private company limited by shares.",
  "Generate a confidentiality clause suitable for an ADGM employment contract.",
];

export default function ClausesPage() {
  const [request, setRequest] = useState("");
  const [docType, setDocType] = useState("articles_of_association");
  const [result, setResult] = useState<ClauseResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const [showSources, setShowSources] = useState(false);

  async function handleGenerate() {
    if (!request.trim() || loading) return;
    setError(null); setResult(null); setLoading(true);
    try { setResult(await generateClause(request, docType)); }
    catch (e: unknown) { setError(e instanceof Error ? e.message : "Generation failed"); }
    finally { setLoading(false); }
  }

  function handleCopy() {
    if (!result) return;
    navigator.clipboard.writeText(result.clause_text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  return (
    <div className="flex flex-col h-full overflow-hidden">
      <TopBar title="Clause Generator" subtitle="Draft ADGM-compliant legal clauses with precise regulatory references" />

      <div className="flex-1 overflow-y-auto px-6 py-6 page-enter">
        <div className="max-w-5xl mx-auto">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Left — input */}
            <div className="space-y-4">
              <div className="card p-5 space-y-4">
                <div className="flex items-center gap-2">
                  <div className="w-8 h-8 rounded-lg bg-violet-50 border border-violet-200 flex items-center justify-center">
                    <Sparkles size={14} className="text-violet-600" />
                  </div>
                  <h3 className="font-display text-sm font-semibold text-[var(--text)]">Clause Request</h3>
                </div>

                <div>
                  <label className="section-label block mb-1.5">Document Type</label>
                  <div className="relative">
                    <select
                      value={docType}
                      onChange={e => setDocType(e.target.value)}
                      className="input-base appearance-none pr-8 cursor-pointer"
                    >
                      {DOC_TYPES.map(d => <option key={d.value} value={d.value}>{d.label}</option>)}
                    </select>
                    <ChevronDown size={13} className="absolute right-3 top-1/2 -translate-y-1/2 text-[var(--text-3)] pointer-events-none" />
                  </div>
                </div>

                <div>
                  <label className="section-label block mb-1.5">Describe the clause you need</label>
                  <textarea
                    value={request}
                    onChange={e => setRequest(e.target.value)}
                    placeholder="e.g. Draft a UBO beneficial ownership disclosure clause…"
                    rows={5}
                    className="input-base resize-none"
                  />
                </div>

                <button
                  onClick={handleGenerate}
                  disabled={!request.trim() || loading}
                  className="w-full py-2.5 rounded-xl text-sm font-semibold flex items-center justify-center gap-2 transition-all border"
                  style={
                    request.trim() && !loading
                      ? { background: "#F5F3FF", borderColor: "#DDD6FE", color: "#7C3AED" }
                      : { background: "var(--surface-alt)", borderColor: "var(--border)", color: "var(--text-3)", cursor: "not-allowed" }
                  }
                >
                  {loading ? <><Loader2 size={14} className="animate-spin" /> Generating…</> : <><Sparkles size={14} /> Generate Clause</>}
                </button>

                {error && (
                  <div className="rounded-xl border border-rose-200 bg-rose-50 p-3 text-xs text-rose-700">{error}</div>
                )}
              </div>

              {/* Examples */}
              <div className="card p-4">
                <p className="section-label mb-3">Example requests</p>
                <div className="space-y-1">
                  {EXAMPLES.map(ex => (
                    <button
                      key={ex}
                      onClick={() => setRequest(ex)}
                      className="w-full text-left text-[12px] text-[var(--text-2)] hover:text-amber-700 px-3 py-2 rounded-lg hover:bg-amber-50 transition-all leading-relaxed"
                    >
                      → {ex}
                    </button>
                  ))}
                </div>
              </div>
            </div>

            {/* Right — output */}
            <div className="space-y-4">
              {!result && !loading && (
                <div className="card rounded-2xl p-12 flex flex-col items-center justify-center text-center gap-4 min-h-[300px]">
                  <div className="w-14 h-14 rounded-2xl bg-violet-50 border border-violet-200 flex items-center justify-center">
                    <Sparkles size={22} className="text-violet-500" />
                  </div>
                  <p className="text-sm text-[var(--text-3)] max-w-xs">
                    Your generated clause will appear here, formatted with ADGM regulatory language and citations.
                  </p>
                </div>
              )}

              {loading && (
                <div className="card rounded-2xl p-12 flex flex-col items-center justify-center gap-4">
                  <div className="w-14 h-14 rounded-2xl bg-violet-50 border border-violet-200 flex items-center justify-center">
                    <Loader2 size={22} className="text-violet-500 animate-spin" />
                  </div>
                  <div className="text-center">
                    <p className="font-display text-sm font-semibold text-[var(--text)] mb-1">Generating your clause…</p>
                    <p className="text-xs text-[var(--text-3)]">Searching regulations · Drafting · Verifying citations</p>
                  </div>
                  <div className="w-48 h-1.5 rounded-full bg-[var(--border)] overflow-hidden">
                    <div className="h-full shimmer rounded-full" />
                  </div>
                </div>
              )}

              {result && (
                <div className="space-y-3">
                  <div className="card rounded-2xl overflow-hidden">
                    <div className="flex items-center justify-between px-5 py-3 border-b border-[var(--border)] bg-[var(--surface-alt)]">
                      <span className="text-xs font-medium text-[var(--text-2)] flex items-center gap-1.5">
                        <Sparkles size={11} className="text-violet-500" /> Generated Clause
                      </span>
                      <div className="flex items-center gap-3">
                        <span className="text-[10.5px] text-[var(--text-3)] flex items-center gap-1">
                          <Clock size={9} /> {formatLatency(result.latency_ms)}
                        </span>
                        <button
                          onClick={handleCopy}
                          className="flex items-center gap-1.5 text-xs text-[var(--text-3)] hover:text-amber-700 transition-colors"
                        >
                          {copied ? <><Check size={11} className="text-jade-600" /> Copied</> : <><Copy size={11} /> Copy</>}
                        </button>
                      </div>
                    </div>
                    <div className="px-5 py-4 prose-adgm max-h-[420px] overflow-y-auto">
                      <ReactMarkdown
                        remarkPlugins={[remarkGfm]}
                        components={citationMarkdownComponents}
                      >
                        {preprocessCitations(result.clause_text)}
                      </ReactMarkdown>
                    </div>
                  </div>

                  {result.citations.length > 0 && (
                    <div className="card rounded-2xl overflow-hidden">
                      <button
                        onClick={() => setShowSources(!showSources)}
                        className="w-full flex items-center justify-between px-5 py-3 text-left"
                      >
                        <span className="text-xs font-medium text-[var(--text-2)] flex items-center gap-1.5">
                          <BookOpen size={11} className="text-amber-600" />
                          Regulatory Sources ({result.citations.length})
                        </span>
                        <ChevronDown size={12} className={`text-[var(--text-3)] transition-transform ${showSources ? "rotate-180" : ""}`} />
                      </button>
                      {showSources && (
                        <div className="px-5 pb-4 space-y-2">
                          {result.citations.map((s, i) => (
                            <div
                              key={i}
                              className="flex items-center gap-2.5 p-2.5 rounded-lg text-xs border border-[var(--border)]"
                              style={{ background: collectionBadgeColor(s.collection) }}
                            >
                              <BookOpen size={10} className="text-amber-600 flex-shrink-0" />
                              <div>
                                <p className="text-[var(--text)] font-medium">{s.source_title}</p>
                                {s.rule_reference && <p className="text-amber-700 text-[10px] mt-0.5">{s.rule_reference}</p>}
                              </div>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
