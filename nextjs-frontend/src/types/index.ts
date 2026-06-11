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
  source_url?: string | null;
  rule_reference?: string | null;
  page_number?: number | null;
  heading?: string | null;
  authority?: string | null;
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
  title: string;
  description: string;
  severity: "high" | "medium" | "low";
  clause_heading: string;
  clause_excerpt: string;
  clause_reference?: string | null;
  violation_type?: string | null;
  regulation_reference?: string | null;
  recommendation: string;
}

export interface Recommendation {
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
  gap_count: number;
  summary: string;
  violation_types: string[];
  regulation_references: string[];
  similarity_score: number;
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
  request: string;
  clause_type: string;
  document_type: string;
  clause_text: string;
  citations: CitationSource[];
  model: string;
  latency_ms: number;
}

// ── Analytics ─────────────────────────────────────────────────────────────────

export interface AnalyticsResult {
  question: string;
  generated_sql: string;
  sql_safe: boolean;
  sql_rejection_reason?: string | null;
  preview_only: boolean;
  query_results: Record<string, unknown>[];
  row_count: number;
  columns: string[];
  answer: string;
  model: string;
  latency_ms: number;
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
