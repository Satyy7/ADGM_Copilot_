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
  if (score >= 80) return "#059669";
  if (score >= 60) return "#D97706";
  if (score >= 40) return "#EA580C";
  return "#E11D48";
}

export function scoreLabel(score: number): string {
  if (score >= 80) return "Compliant";
  if (score >= 60) return "Partially Compliant";
  if (score >= 40) return "Needs Attention";
  return "Non-Compliant";
}

export function severityColor(severity: string): { bg: string; text: string; border: string } {
  switch (severity.toLowerCase()) {
    case "critical": return { bg: "#FFF1F2", text: "#BE123C", border: "#FECDD3" };
    case "high":     return { bg: "#FFF7ED", text: "#C2410C", border: "#FED7AA" };
    case "medium":   return { bg: "#FFFBEB", text: "#B45309", border: "#FDE68A" };
    case "low":      return { bg: "#ECFDF5", text: "#047857", border: "#A7F3D0" };
    default:         return { bg: "#FAF8F2", text: "#6B6259", border: "#EDE9DF" };
  }
}

export function priorityColor(priority: string): { bg: string; text: string; border: string } {
  switch (priority.toLowerCase()) {
    case "immediate": return { bg: "#FFF1F2", text: "#BE123C", border: "#FECDD3" };
    case "high":      return { bg: "#FFF7ED", text: "#C2410C", border: "#FED7AA" };
    case "medium":    return { bg: "#FFFBEB", text: "#B45309", border: "#FDE68A" };
    case "low":       return { bg: "#ECFDF5", text: "#047857", border: "#A7F3D0" };
    default:          return { bg: "#FAF8F2", text: "#6B6259", border: "#EDE9DF" };
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
    regulations:        "#FFFBEB",
    guidance:           "#ECFDF5",
    templates:          "#F0F9FF",
    checklists:         "#F5F3FF",
    historical_reviews: "#FFF7ED",
  };
  return map[collection] ?? "#FAF8F2";
}
