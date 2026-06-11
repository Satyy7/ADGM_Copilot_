import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatLatency(ms: number): string {
  if (ms < 1000) return `${ms.toFixed(0)}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
}

export function scoreColor(score: number): string {
  if (score >= 80) return "#34d4a0";
  if (score >= 60) return "#f0c050";
  if (score >= 40) return "#ffb040";
  return "#ff5c6e";
}

export function scoreLabel(score: number): string {
  if (score >= 80) return "Compliant";
  if (score >= 60) return "Partially Compliant";
  if (score >= 40) return "Needs Attention";
  return "Non-Compliant";
}

export function severityColor(severity: string): { bg: string; text: string; border: string } {
  switch (severity.toLowerCase()) {
    case "critical": return { bg: "rgba(232,58,80,0.12)", text: "#ff5c6e", border: "rgba(232,58,80,0.3)" };
    case "high":     return { bg: "rgba(255,140,0,0.12)",  text: "#ffb040", border: "rgba(255,140,0,0.3)" };
    case "medium":   return { bg: "rgba(240,192,80,0.12)", text: "#f0c050", border: "rgba(240,192,80,0.3)" };
    case "low":      return { bg: "rgba(52,212,160,0.12)", text: "#34d4a0", border: "rgba(52,212,160,0.3)" };
    default:         return { bg: "rgba(136,153,187,0.12)", text: "#8899bb", border: "rgba(136,153,187,0.3)" };
  }
}

export function priorityColor(priority: string): { bg: string; text: string; border: string } {
  switch (priority.toLowerCase()) {
    case "immediate": return { bg: "rgba(232,58,80,0.12)", text: "#ff5c6e", border: "rgba(232,58,80,0.3)" };
    case "high":      return { bg: "rgba(255,140,0,0.12)",  text: "#ffb040", border: "rgba(255,140,0,0.3)" };
    case "medium":    return { bg: "rgba(240,192,80,0.12)", text: "#f0c050", border: "rgba(240,192,80,0.3)" };
    case "low":       return { bg: "rgba(52,212,160,0.12)", text: "#34d4a0", border: "rgba(52,212,160,0.3)" };
    default:          return { bg: "rgba(136,153,187,0.12)", text: "#8899bb", border: "rgba(136,153,187,0.3)" };
  }
}

export function highlightSql(sql: string): string {
  const keywords = /\b(SELECT|FROM|WHERE|JOIN|LEFT|RIGHT|INNER|OUTER|ON|AND|OR|NOT|IN|IS|NULL|AS|ORDER|BY|GROUP|HAVING|LIMIT|OFFSET|DISTINCT|COUNT|SUM|AVG|MIN|MAX|CASE|WHEN|THEN|ELSE|END|INSERT|UPDATE|DELETE|CREATE|DROP|ALTER|TABLE|INDEX|WITH|UNION|ALL|EXISTS|BETWEEN|LIKE|ILIKE|CAST|COALESCE|NULLIF|EXTRACT|DATE|NOW|CURRENT_DATE)\b/gi;
  const strings = /'[^']*'/g;
  const numbers = /\b(\d+(\.\d+)?)\b/g;

  return sql
    .replace(strings,  (m) => `<span class="sql-string">${m}</span>`)
    .replace(keywords, (m) => `<span class="sql-keyword">${m.toUpperCase()}</span>`)
    .replace(numbers,  (m) => `<span class="sql-number">${m}</span>`);
}

export function truncate(text: string, max: number): string {
  return text.length > max ? text.slice(0, max) + "…" : text;
}

export function collectionBadgeColor(collection: string): string {
  const map: Record<string, string> = {
    regulations:        "rgba(212,160,48,0.15)",
    guidance:           "rgba(52,212,160,0.12)",
    templates:          "rgba(100,149,237,0.15)",
    checklists:         "rgba(147,112,219,0.15)",
    historical_reviews: "rgba(255,140,0,0.12)",
  };
  return map[collection] ?? "rgba(136,153,187,0.12)";
}
