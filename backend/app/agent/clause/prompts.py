"""LLM prompts for the clause generator pipeline (Phase 10)."""

PARSE_REQUEST_PROMPT = """\
Extract structured metadata from the following clause generation request.

Request: {request}

Return ONLY a valid JSON object with exactly these keys:
- "clause_type": a concise snake_case identifier for the clause \
(e.g. "ubo_disclosure", "share_transfer_restriction", "employment_probation", \
"non_compete", "dividend_policy", "board_composition", "liquidation_preference")
- "document_type": the target document \
(e.g. "articles_of_association", "employment_contract", "shareholders_agreement", \
"memorandum_of_association", "ubo_declaration", "general")
- "key_requirements": a JSON array of 3 to 5 specific requirements the clause must address (strings)

Example:
{{"clause_type": "ubo_disclosure", "document_type": "articles_of_association", \
"key_requirements": ["identify UBOs with 25% or more ownership", \
"provide passport and Emirates ID copies", "annual update obligation"]}}

JSON object:"""


GENERATE_CLAUSE_PROMPT = """\
You are an expert ADGM legal drafter with deep knowledge of Abu Dhabi Global Market \
regulations, company law, and employment law.

=== REGULATORY CONTEXT AND TEMPLATES ===
{context}
=== END CONTEXT ===

Draft a legally compliant clause for inclusion in a {document_type}.

Clause requested: {request}
Clause type: {clause_type}
Key requirements to address:
{key_requirements}

DRAFTING RULES — follow all of these strictly:
1. Use formal legal language appropriate for a {document_type}.
2. Begin with a numbered placeholder heading: "Article [X] — <Clause Title>" or \
"Clause [X] — <Clause Title>".
3. Cite every ADGM regulatory requirement inline using the format: \
[Source: <document title>, <article/rule reference>].
4. Address EVERY key requirement listed above — do not skip any.
5. Do not invent or fabricate any regulatory references not present in the context above.
6. If the context lacks sufficient regulatory grounding for a requirement, \
note "[Verify against current ADGM regulations]" at the relevant point.
7. The clause must be self-contained and ready to insert directly into the document.

Drafted clause:"""
