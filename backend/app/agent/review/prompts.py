"""LLM prompts for the six compliance review sub-agents (Phase 9).

Each prompt is designed to return structured JSON so the calling node
can parse it deterministically.  Prompts are kept here to make iteration
easy — improving prompt quality never requires touching node logic.
"""

CLASSIFY_PROMPT = """\
You are an ADGM compliance specialist.

Identify the document type of the following legal document (first 1500 characters shown).

Document:
{text}

Choose the single best match from exactly these identifiers:
- articles_of_association
- memorandum_of_association
- employment_contract
- ubo_declaration
- board_resolution
- shareholder_resolution
- share_purchase_agreement
- other

Reply with ONLY the identifier (e.g. articles_of_association). No explanation."""


EXTRACT_CLAUSES_PROMPT = """\
You are an ADGM compliance specialist analyzing a {document_type}.

Extract the 8 to 15 most legally significant clauses from the document below.
Focus on: governance, ownership structure, compliance obligations, employment terms,
disclosure requirements, and regulatory duties.

Document text:
{text}

Return ONLY a valid JSON array. Each item must have exactly these keys:
- "heading": article or section heading (string)
- "text": clause text, max 250 characters (string)
- "category": one of "governance", "ownership", "employment", "compliance", "other"

Example:
[
  {{"heading": "Article 3 - Share Capital", "text": "The share capital is...", "category": "governance"}}
]

JSON array:"""


DETECT_VIOLATIONS_PROMPT = """\
You are a senior ADGM compliance officer.

Document type: {document_type}

Relevant ADGM regulations retrieved from the knowledge base:
{regulations}

Clauses extracted from the document under review:
{clauses}

Identify every compliance violation — clauses that conflict with, omit, or inadequately
address ADGM requirements based on the regulations above.

Return ONLY a valid JSON array. Each violation must have exactly these keys:
- "clause_heading": the article/section heading (string)
- "clause_excerpt": relevant excerpt, max 200 characters (string)
- "violation_type": one of "non_compliant_clause", "missing_disclosure", "inadequate_provision", "prohibited_term"
- "severity": one of "high", "medium", "low"
- "title": short violation title, max 100 characters (string)
- "description": detailed explanation citing the specific ADGM requirement breached (string)
- "regulation_reference": specific ADGM regulation or article violated (string or null)
- "recommendation": specific corrective action (string)

If no violations are found return an empty array: []

JSON array:"""


ANALYSE_GAPS_PROMPT = """\
You are a senior ADGM compliance officer reviewing a {document_type}.

This document contains the following clause headings:
{clause_headings}

For a fully ADGM-compliant {document_type}, identify what mandatory provisions are MISSING.
Reference specific ADGM regulations, rules, or guidelines that require each missing provision.

Return ONLY a valid JSON array. Each gap must have exactly these keys:
- "missing_provision": what is missing (string)
- "severity": one of "high", "medium", "low"
- "regulation_reference": ADGM regulation requiring this provision (string or null)
- "recommendation": what to add to the document (string)

If nothing mandatory is missing return an empty array: []

JSON array:"""


GENERATE_SUMMARY_PROMPT = """\
You are a senior ADGM compliance officer.

You have just reviewed a {document_type} and found:
- {violation_count} violation(s): {violations_brief}
- {gap_count} missing provision(s): {gaps_brief}

Write a concise executive summary (3 to 5 sentences) for a compliance officer.
The summary must:
1. State the document type and overall compliance status
2. Highlight the most critical issues found (cite specific ADGM requirements)
3. State the recommended immediate actions

Reply with ONLY the summary paragraph. No bullet points, no headers."""
