"""Clause generator pipeline nodes (Phase 10).

Pipeline
--------
parse_request → retrieve_context → generate_clause

Node 1 — parse_request
    LLM extracts structured metadata from the natural language request:
    clause_type, document_type, key_requirements.

Node 2 — retrieve_context
    Searches BOTH regulations (legal grounding) AND templates (style/structure
    reference) collections.  Combining both gives the LLM accurate regulatory
    requirements AND real ADGM document language to model.

Node 3 — generate_clause
    A dedicated legal-drafter prompt drives the LLM to produce a numbered,
    citation-backed clause ready to paste into a document.

All nodes are closures returned by ``build_clause_nodes(retriever, gemini)``
so they share services without relying on global state.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from backend.app.agent.clause.prompts import GENERATE_CLAUSE_PROMPT, PARSE_REQUEST_PROMPT
from backend.app.schemas.rag import CitationSource, RetrievedChunk
from backend.app.services.retrieval import Retriever

logger = logging.getLogger(__name__)

# Retrieve from both regulatory and template collections for clause drafting
_CLAUSE_COLLECTIONS = ["regulations", "guidance", "templates", "checklists"]


def build_clause_nodes(retriever: Retriever, gemini: object) -> dict[str, Any]:
    """Return node name → callable map for the clause generator sub-graph.

    Parameters
    ----------
    retriever:
        Any ``Retriever``-protocol object (RerankedRetriever in production).
    gemini:
        ``GeminiClient`` instance (typed as object to avoid circular import).
    """

    # ── Node 1: parse_request ─────────────────────────────────────────────────

    def parse_request(state: dict) -> dict:
        """Extract clause_type, document_type, and key_requirements from the request."""
        request = state.get("request", "")
        doc_type_hint = state.get("document_type_hint", "")

        hint_text = f"\nHint — the caller specified document_type: {doc_type_hint}" if doc_type_hint else ""
        prompt = PARSE_REQUEST_PROMPT.format(request=request + hint_text)

        try:
            raw = gemini.generate_text(prompt)  # type: ignore[union-attr]
            parsed = _parse_json_object(raw)
            clause_type   = parsed.get("clause_type", "general_clause")
            document_type = parsed.get("document_type", doc_type_hint or "general")
            key_requirements = parsed.get("key_requirements", [])
        except Exception as exc:
            logger.warning("parse_request failed (%s), using defaults.", exc)
            clause_type      = "general_clause"
            document_type    = doc_type_hint or "general"
            key_requirements = []

        logger.info(
            "Parsed clause request — type=%s  doc=%s  requirements=%d",
            clause_type, document_type, len(key_requirements),
        )
        return {
            "clause_type":       clause_type,
            "document_type":     document_type,
            "key_requirements":  key_requirements,
        }

    # ── Node 2: retrieve_context ──────────────────────────────────────────────

    def retrieve_context(state: dict) -> dict:
        """Retrieve relevant regulations and templates for clause drafting."""
        request       = state.get("request", "")
        clause_type   = state.get("clause_type", "")
        document_type = state.get("document_type", "")
        top_k         = state.get("top_k", 8)

        # Craft a rich retrieval query combining the request, clause type, and document type
        query = f"{document_type} {clause_type} {request}"

        try:
            chunks: list[RetrievedChunk] = retriever.search(
                question=query,
                collections=_CLAUSE_COLLECTIONS,
                top_k=top_k,
            )
        except Exception as exc:
            logger.warning("retrieve_context failed (%s), using empty chunks.", exc)
            chunks = []

        logger.info(
            "Retrieved %d context chunks for clause generation.", len(chunks)
        )
        return {"retrieved_chunks": chunks}

    # ── Node 3: generate_clause ───────────────────────────────────────────────

    def generate_clause(state: dict) -> dict:
        """Draft the ADGM-compliant clause from regulatory context."""
        request          = state.get("request", "")
        clause_type      = state.get("clause_type", "general_clause")
        document_type    = state.get("document_type", "general")
        key_requirements = state.get("key_requirements", [])
        chunks           = state.get("retrieved_chunks", [])

        context = _format_context(chunks)
        requirements_text = "\n".join(f"  - {r}" for r in key_requirements) or "  - (No specific requirements parsed)"

        prompt = GENERATE_CLAUSE_PROMPT.format(
            context=context or "No regulatory context retrieved — use general ADGM principles.",
            document_type=document_type,
            request=request,
            clause_type=clause_type,
            key_requirements=requirements_text,
        )

        try:
            clause_text: str = gemini.generate_text(prompt)  # type: ignore[union-attr]
        except Exception as exc:
            logger.error("generate_clause LLM call failed: %s", exc)
            clause_text = (
                f"[Clause generation failed: {exc}. "
                "Please retry or contact the compliance team.]"
            )

        citations = _deduplicate_citations(chunks)
        model: str = getattr(gemini, "active_model", "unknown")  # type: ignore[union-attr]

        logger.info(
            "Clause generated — type=%s  citations=%d  chars=%d",
            clause_type, len(citations), len(clause_text),
        )
        return {
            "clause_text": clause_text.strip(),
            "citations":   citations,
            "model":       model,
        }

    return {
        "parse_request":    parse_request,
        "retrieve_context": retrieve_context,
        "generate_clause":  generate_clause,
    }


# ── Helpers ────────────────────────────────────────────────────────────────────

def _parse_json_object(raw: str) -> dict:
    """Extract a JSON object from an LLM response with multiple fallback strategies."""
    text = raw.strip()
    try:
        result = json.loads(text)
        if isinstance(result, dict):
            return result
    except json.JSONDecodeError:
        pass
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            result = json.loads(match.group(0))
            if isinstance(result, dict):
                return result
        except json.JSONDecodeError:
            pass
    logger.warning("Could not parse JSON object from LLM response: %.120s…", text)
    return {}


def _format_context(chunks: list[RetrievedChunk]) -> str:
    """Format retrieved chunks into a numbered context block for the clause prompt."""
    parts: list[str] = []
    for i, chunk in enumerate(chunks, 1):
        header_parts = []
        if chunk.source_title:
            header_parts.append(f"Source: {chunk.source_title}")
        if chunk.rule_reference:
            header_parts.append(f"Ref: {chunk.rule_reference}")
        if chunk.collection:
            header_parts.append(f"Collection: {chunk.collection}")
        header = " | ".join(header_parts) if header_parts else f"Chunk {i}"
        parts.append(f"[{i}] {header}\n{chunk.text.strip()}")
    return "\n\n".join(parts)


def _deduplicate_citations(chunks: list[RetrievedChunk]) -> list[CitationSource]:
    """Build deduplicated citation list from retrieved chunks."""
    seen: set[tuple[str, str, str]] = set()
    citations: list[CitationSource] = []
    for chunk in chunks:
        key = (chunk.source_title or "", chunk.rule_reference or "", chunk.collection)
        if key not in seen:
            seen.add(key)
            citations.append(
                CitationSource(
                    source_title=chunk.source_title or chunk.collection,
                    source_url=chunk.source_url,
                    rule_reference=chunk.rule_reference,
                    collection=chunk.collection,
                    authority=chunk.authority,
                )
            )
    return citations
