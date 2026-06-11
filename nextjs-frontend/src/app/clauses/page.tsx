"use client";
import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Wand2, Copy, Check, BookOpen, Clock, Cpu, ChevronDown } from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import TopBar from "@/components/layout/TopBar";
import { generateClause } from "@/lib/api";
import type { ClauseResult } from "@/types";
import { cn, formatLatency, collectionBadgeColor } from "@/lib/utils";

const DOC_TYPES = [
  { value: "articles_of_association", label: "Articles of Association" },
  { value: "memorandum_of_association", label: "Memorandum of Association" },
  { value: "employment_contract", label: "Employment Contract" },
  { value: "board_resolution", label: "Board Resolution" },
  { value: "shareholder_resolution", label: "Shareholder Resolution" },
  { value: "ubo_declaration", label: "UBO Declaration" },
  { value: "", label: "General / Other" },
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
    setError(null);
    setResult(null);
    setLoading(true);
    try {
      const r = await generateClause(request, docType);
      setResult(r);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Generation failed");
    } finally {
      setLoading(false);
    }
  }

  function handleCopy() {
    if (!result) return;
    navigator.clipboard.writeText(result.clause_text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  return (
    <div className="flex flex-col h-full overflow-hidden">
      <TopBar title="Clause Generator" subtitle="ADGM-compliant legal clauses with full citations" />

      <div className="flex-1 overflow-y-auto px-6 py-6">
        <div className="max-w-5xl mx-auto">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 page-enter">
            {/* Left panel — input */}
            <div className="space-y-4">
              <div className="glass rounded-2xl p-5 space-y-4">
                <div className="flex items-center gap-2 mb-1">
                  <Wand2 size={16} className="text-purple-400" />
                  <h3 className="text-sm font-semibold text-white">Clause Request</h3>
                </div>

                {/* Document type */}
                <div>
                  <label className="text-xs text-slate-500 block mb-1.5">Document Type</label>
                  <div className="relative">
                    <select
                      value={docType}
                      onChange={e => setDocType(e.target.value)}
                      className="w-full bg-navy-800/80 border border-white/8 rounded-xl px-4 py-2.5 text-sm text-slate-300 focus:outline-none focus:border-purple-400/40 appearance-none cursor-pointer"
                    >
                      {DOC_TYPES.map(d => (
                        <option key={d.value} value={d.value} className="bg-navy-900">{d.label}</option>
                      ))}
                    </select>
                    <ChevronDown size={14} className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 pointer-events-none" />
                  </div>
                </div>

                {/* Request textarea */}
                <div>
                  <label className="text-xs text-slate-500 block mb-1.5">Describe the clause you need</label>
                  <textarea
                    value={request}
                    onChange={e => setRequest(e.target.value)}
                    placeholder="e.g. Draft a UBO beneficial ownership disclosure clause…"
                    rows={5}
                    className="w-full bg-navy-800/80 border border-white/8 rounded-xl px-4 py-3 text-sm text-white placeholder:text-slate-600 focus:outline-none focus:border-purple-400/40 resize-none transition-all"
                  />
                </div>

                <motion.button
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                  onClick={handleGenerate}
                  disabled={!request.trim() || loading}
                  className={cn(
                    "w-full py-2.5 rounded-xl text-sm font-semibold flex items-center justify-center gap-2 transition-all",
                    request.trim() && !loading
                      ? "bg-purple-500/20 border border-purple-400/30 text-purple-300 hover:bg-purple-500/30"
                      : "bg-navy-700/50 border border-white/5 text-slate-600 cursor-not-allowed"
                  )}
                >
                  {loading ? (
                    <><Cpu size={15} className="animate-spin-slow" /> Generating…</>
                  ) : (
                    <><Wand2 size={15} /> Generate Clause</>
                  )}
                </motion.button>

                {error && (
                  <div className="rounded-xl border border-crimson-500/30 bg-crimson-500/8 p-3 text-xs text-crimson-400">
                    {error}
                  </div>
                )}
              </div>

              {/* Example prompts */}
              <div className="glass rounded-2xl p-4">
                <p className="text-xs text-slate-500 mb-3 font-medium">Example requests</p>
                <div className="space-y-1.5">
                  {EXAMPLES.map(ex => (
                    <button
                      key={ex}
                      onClick={() => setRequest(ex)}
                      className="w-full text-left text-xs text-slate-500 hover:text-slate-300 px-3 py-2 rounded-lg hover:bg-white/4 transition-all leading-relaxed"
                    >
                      → {ex}
                    </button>
                  ))}
                </div>
              </div>
            </div>

            {/* Right panel — output */}
            <div className="space-y-4">
              {!result && !loading && (
                <div className="glass rounded-2xl p-12 flex flex-col items-center justify-center text-center gap-4 h-full min-h-[300px]">
                  <div className="w-14 h-14 rounded-2xl bg-purple-400/10 border border-purple-400/20 flex items-center justify-center animate-float">
                    <Wand2 size={22} className="text-purple-400" />
                  </div>
                  <p className="text-sm text-slate-500 max-w-xs">
                    Your generated clause will appear here, formatted with ADGM-specific regulatory language and citations.
                  </p>
                </div>
              )}

              {loading && (
                <div className="glass rounded-2xl p-12 flex flex-col items-center justify-center gap-4">
                  <div className="w-14 h-14 rounded-2xl bg-purple-400/10 border border-purple-400/20 flex items-center justify-center">
                    <Cpu size={22} className="text-purple-400 animate-spin-slow" />
                  </div>
                  <div className="text-center">
                    <p className="text-sm text-white mb-1">Retrieving regulatory context…</p>
                    <p className="text-xs text-slate-500">HyDE → Hybrid Search → Re-rank → Generate</p>
                  </div>
                  <div className="w-48 h-1 rounded-full bg-navy-700 overflow-hidden">
                    <div className="h-full shimmer rounded-full" />
                  </div>
                </div>
              )}

              <AnimatePresence>
                {result && (
                  <motion.div
                    initial={{ opacity: 0, y: 16 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="space-y-3"
                  >
                    {/* Output card */}
                    <div className="glass rounded-2xl overflow-hidden">
                      {/* Toolbar */}
                      <div className="flex items-center justify-between px-5 py-3 border-b border-white/5">
                        <span className="text-xs font-medium text-slate-400 flex items-center gap-1.5">
                          <Wand2 size={12} className="text-purple-400" /> Generated Clause
                        </span>
                        <div className="flex items-center gap-3">
                          <span className="text-xs text-slate-600 flex items-center gap-1">
                            <Clock size={10} /> {formatLatency(result.latency_ms)}
                          </span>
                          <button
                            onClick={handleCopy}
                            className="flex items-center gap-1.5 text-xs text-slate-400 hover:text-slate-200 transition-colors"
                          >
                            {copied ? <><Check size={12} className="text-jade-400" /> Copied</> : <><Copy size={12} /> Copy</>}
                          </button>
                        </div>
                      </div>

                      {/* Clause text */}
                      <div className="px-5 py-4 prose-adgm max-h-[420px] overflow-y-auto">
                        <ReactMarkdown remarkPlugins={[remarkGfm]}>{result.clause_text}</ReactMarkdown>
                      </div>
                    </div>

                    {/* Sources */}
                    {result.citations.length > 0 && (
                      <div className="glass rounded-2xl overflow-hidden">
                        <button
                          onClick={() => setShowSources(!showSources)}
                          className="w-full flex items-center justify-between px-5 py-3 text-left"
                        >
                          <span className="text-xs font-medium text-slate-400 flex items-center gap-1.5">
                            <BookOpen size={12} className="text-gold-400" />
                            Regulatory Sources ({result.citations.length})
                          </span>
                          <ChevronDown size={13} className={cn("text-slate-500 transition-transform", showSources && "rotate-180")} />
                        </button>
                        <AnimatePresence>
                          {showSources && (
                            <motion.div
                              initial={{ height: 0 }}
                              animate={{ height: "auto" }}
                              exit={{ height: 0 }}
                              className="overflow-hidden"
                            >
                              <div className="px-5 pb-4 space-y-2">
                                {result.citations.map((s, i) => (
                                  <div
                                    key={i}
                                    className="flex items-center gap-2.5 p-2.5 rounded-lg text-xs"
                                    style={{ background: collectionBadgeColor(s.collection) }}
                                  >
                                    <BookOpen size={11} className="text-gold-400 flex-shrink-0" />
                                    <div>
                                      <p className="text-slate-300 font-medium">{s.source_title}</p>
                                      {s.rule_reference && <p className="text-gold-400 text-[10px] mt-0.5">{s.rule_reference}</p>}
                                    </div>
                                  </div>
                                ))}
                              </div>
                            </motion.div>
                          )}
                        </AnimatePresence>
                      </div>
                    )}
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
