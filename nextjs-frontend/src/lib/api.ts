import type {
  ChatResponse, ReviewReport, ClauseResult,
  AnalyticsResult, CaseSearchResult, CacheStats,
} from "@/types";

const BASE = "/api/backend";

async function post<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail ?? `HTTP ${res.status}`);
  }
  return res.json();
}

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`);
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail ?? `HTTP ${res.status}`);
  }
  return res.json();
}

async function del<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`, { method: "DELETE" });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

// ── Chat ──────────────────────────────────────────────────────────────────────

export async function sendChatMessage(
  question: string,
  topK = 5,
): Promise<ChatResponse> {
  return post<ChatResponse>("/chat", { question, top_k: topK });
}

// ── Review ────────────────────────────────────────────────────────────────────

export async function reviewDocument(file: File): Promise<ReviewReport> {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(`${BASE}/reviews/analyze`, {
    method: "POST",
    body: form,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail ?? `HTTP ${res.status}`);
  }
  return res.json();
}

// ── Clauses ───────────────────────────────────────────────────────────────────

export async function generateClause(
  request: string,
  documentType: string,
  topK = 8,
): Promise<ClauseResult> {
  return post<ClauseResult>("/generated-clauses/generate", {
    request,
    document_type: documentType || undefined,
    top_k: topK,
  });
}

// ── Analytics ─────────────────────────────────────────────────────────────────

export async function runAnalyticsQuery(
  question: string,
  previewOnly = false,
  confirmedSql?: string,
): Promise<AnalyticsResult> {
  return post<AnalyticsResult>("/analytics/query", {
    question,
    preview_only: previewOnly,
    confirmed_sql: confirmedSql || undefined,
  });
}

// ── Cases ─────────────────────────────────────────────────────────────────────

export async function searchCases(
  query: string,
  topK = 5,
): Promise<CaseSearchResult> {
  return post<CaseSearchResult>("/cases/search", { query, top_k: topK });
}

// ── Cache ─────────────────────────────────────────────────────────────────────

export async function getCacheStats(): Promise<CacheStats> {
  return get<CacheStats>("/cache/stats");
}

export async function flushCache(namespace?: string): Promise<{ total_deleted?: number; deleted_keys?: number }> {
  return del(namespace ? `/cache/flush/${namespace}` : "/cache/flush");
}
