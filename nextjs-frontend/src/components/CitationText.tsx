/**
 * Inline citation styling for LLM-generated text.
 *
 * The agents embed citations in the format:
 *   [Source: ADGM Companies Regulations 2020, Article 52(3)]
 *
 * Two rendering modes:
 * 1. ReactMarkdown — use `preprocessCitations` + `citationMarkdownComponents`
 * 2. Plain text     — use the `<CitationText>` component directly
 */

import type { Components } from "react-markdown";

// ── Shared visual style ────────────────────────────────────────────────────────

const CITATION_STYLE: React.CSSProperties = {
  color: "#1c1917",          // stone-950 — warm near-black, not pure black
  fontStyle: "italic",
  fontSize: "0.82em",
  letterSpacing: "-0.01em",
  whiteSpace: "nowrap",
};

const SECTION_SIGN_STYLE: React.CSSProperties = {
  color: "#92400e",          // amber-900 — slightly warmer than the text
  fontStyle: "normal",
  marginRight: "2px",
  fontSize: "0.9em",
};

// ── Inline span used by both modes ────────────────────────────────────────────

export function InlineCitation({ children }: { children: React.ReactNode }) {
  return (
    <span style={CITATION_STYLE}>
      <span style={SECTION_SIGN_STYLE}>§</span>
      {children}
    </span>
  );
}

// ── Mode 1: ReactMarkdown helpers ─────────────────────────────────────────────

const CITE_PREFIX = "§CITE:";

/**
 * Replace [Source: X] patterns with backtick-wrapped markers that
 * `citationMarkdownComponents` will intercept and style.
 */
export function preprocessCitations(text: string): string {
  return text.replace(
    /\[Source:\s*([^\]]+)\]/g,
    (_, content: string) => `\`${CITE_PREFIX}${content.trim()}\``
  );
}

/**
 * Pass as the `components` prop to ReactMarkdown.
 * Intercepts inline code that starts with our marker; leaves real code alone.
 */
export const citationMarkdownComponents: Components = {
  code({ children, className, ...rest }) {
    const text = String(children);
    if (!className && text.startsWith(CITE_PREFIX)) {
      return <InlineCitation>{text.slice(CITE_PREFIX.length)}</InlineCitation>;
    }
    return (
      <code className={className} {...rest}>
        {children}
      </code>
    );
  },
};

// ── Mode 2: Plain-text component ──────────────────────────────────────────────

const SOURCE_RE = /(\[Source:[^\]]+\])/g;

interface CitationTextProps {
  text: string;
  className?: string;
}

/**
 * Renders plain text with [Source: ...] patterns styled as inline citations.
 * Use this wherever you render agent text outside of ReactMarkdown.
 */
export function CitationText({ text, className }: CitationTextProps) {
  const parts = text.split(SOURCE_RE);
  return (
    <span className={className}>
      {parts.map((part, i) => {
        const match = part.match(/^\[Source:\s*([^\]]+)\]$/);
        if (match) {
          return <InlineCitation key={i}>{match[1].trim()}</InlineCitation>;
        }
        return <span key={i}>{part}</span>;
      })}
    </span>
  );
}
