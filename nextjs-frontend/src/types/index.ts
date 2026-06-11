// ── Chat ─────────────────────────────────────────────────────────────────────

export interface CitationSource {
  source_title: string;
  source_url?: string | null;
  rule_reference?: string | null;
  collection: string;
  authority?: string | null;
}

export interface RetrievedChunk {
  chunk_id: string;
  collection: string;
  text: string;
  score: number;
  source_title?: string | null;
  rule_reference?: string | null;
  heading?: string | null;
}

export interface ChatResponse {
  question: string;
  answer: string;
  sources: CitationSource[];
  retrieved_chunks: RetrievedChunk[];
  chunks_used: number;
  latency_ms: number;
  model: string;
  collections_searched: string[];
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  sources?: CitationSource[];
  model?: string;
  latency_ms?: number;
  timestamp: Date;
}

// ── Review ────────────────────────────────────────────────────────────────────

export interface Violation {
  id?: string;
  title: string;
  description: string;
  severity: "critical" | "high" | "medium" | "low";
  clause_reference?: string | null;
  regulation_reference?: string | null;
  violation_type?: string | null;
}

export interface Recommendation {
  id?: string;
  title: string;
  description: string;
  priority: "immediate" | "high" | "medium" | "low";
  action_required?: string | null;
}

export interface SimilarCase {
  document_name: string;
  document_type: string;
  compliance_score: number;
  violation_count: number;
  similarity_score: number;
  summary?: string | null;
}

export interface ReviewReport {
  document_name: string;
  document_type: string;
  compliance_score: number;
  summary: string;
  violations: Violation[];
  recommendations: Recommendation[];
  similar_cases: SimilarCase[];
  latency_ms: number;
  model: string;
}

// ── Clauses ───────────────────────────────────────────────────────────────────

export interface ClauseResult {
  clause_text: string;
  citations: CitationSource[];
  model: string;
  latency_ms: number;
}

// ── Analytics ─────────────────────────────────────────────────────────────────

export interface AnalyticsResult {
  question: string;
  generated_sql?: string | null;
  sql_safe: boolean;
  sql_rejection_reason?: string | null;
  preview_only: boolean;
  query_results?: Record<string, unknown>[] | null;
  row_count?: number | null;
  columns?: string[] | null;
  execution_error?: string | null;
  answer: string;
  model: string;
}

// ── Cases ─────────────────────────────────────────────────────────────────────

export interface CaseSearchResult {
  query: string;
  results: SimilarCase[];
  count: number;
}

// ── Cache ─────────────────────────────────────────────────────────────────────

export interface CacheStats {
  namespaces: { embeddings: number; generate_text: number; retrieval: number };
  total_cached_keys: number;
  ttl_seconds: { embeddings: number; generate_text: number; retrieval: number };
  memory: { used_memory_human: string; used_memory_peak_human: string; maxmemory_human: string };
}
