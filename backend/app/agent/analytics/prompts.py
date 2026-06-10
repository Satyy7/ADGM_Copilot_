"""Text2SQL analytics prompts — Phase 12.

Two prompts:
  SQL_GENERATION_PROMPT   — converts natural language to a safe SELECT statement
  FORMAT_ANSWER_PROMPT    — converts raw SQL results to a human-readable answer
"""

# Full schema provided to the LLM so it can generate accurate column references.
# Only query-relevant columns are listed (JSONB payloads omitted to save tokens).
_DB_SCHEMA = """\
TABLE: users
  id UUID, email VARCHAR, full_name VARCHAR, organization VARCHAR,
  role VARCHAR, is_active BOOLEAN, created_at TIMESTAMPTZ, updated_at TIMESTAMPTZ

TABLE: documents
  id UUID, user_id UUID, original_filename VARCHAR, mime_type VARCHAR,
  file_extension VARCHAR, file_size_bytes BIGINT, detected_document_type VARCHAR,
  extraction_status VARCHAR, created_at TIMESTAMPTZ, updated_at TIMESTAMPTZ

TABLE: reviews
  id UUID, document_id UUID, user_id UUID, review_type VARCHAR,
  status VARCHAR, compliance_score NUMERIC(5,2), summary TEXT,
  started_at TIMESTAMPTZ, completed_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ, updated_at TIMESTAMPTZ

TABLE: violations
  id UUID, review_id UUID, violation_type VARCHAR, severity VARCHAR,
  title VARCHAR, description TEXT, regulation_reference VARCHAR,
  status VARCHAR, created_at TIMESTAMPTZ, updated_at TIMESTAMPTZ

TABLE: recommendations
  id UUID, review_id UUID, violation_id UUID, title VARCHAR,
  recommendation_text TEXT, priority VARCHAR, status VARCHAR,
  created_at TIMESTAMPTZ, updated_at TIMESTAMPTZ

TABLE: generated_clauses
  id UUID, user_id UUID, request_text TEXT, clause_type VARCHAR,
  generated_text TEXT, model_name VARCHAR, validation_status VARCHAR,
  created_at TIMESTAMPTZ, updated_at TIMESTAMPTZ

TABLE: audit_logs
  id UUID, user_id UUID, action VARCHAR, resource_type VARCHAR,
  resource_id VARCHAR, actor_ip VARCHAR,
  created_at TIMESTAMPTZ, updated_at TIMESTAMPTZ

TABLE: query_logs
  id UUID, user_id UUID, query_type VARCHAR, question TEXT,
  response_text TEXT, generated_sql TEXT, sql_approved BOOLEAN,
  sql_executed BOOLEAN, latency_ms INTEGER, model_name VARCHAR,
  error_message TEXT, created_at TIMESTAMPTZ, updated_at TIMESTAMPTZ
"""

SQL_GENERATION_PROMPT = """\
You are an ADGM Compliance Database Analyst. Convert the compliance analytics \
question into a precise, read-only SQL query for PostgreSQL.

DATABASE SCHEMA:
{schema}

RULES:
1. Only SELECT statements. NEVER use INSERT, UPDATE, DELETE, DROP, ALTER, \
TRUNCATE, CREATE, EXEC, EXECUTE, CALL, GRANT, REVOKE.
2. Cast UUIDs to text: CAST(id AS TEXT) AS id.
3. Format timestamps: TO_CHAR(created_at, 'YYYY-MM-DD HH24:MI') AS created_at.
4. Cast NUMERIC to FLOAT where needed: CAST(compliance_score AS FLOAT).
5. For aggregation queries (COUNT/SUM/AVG/MIN/MAX) do NOT add LIMIT.
6. For all other queries add LIMIT 50 unless the question asks for more.
7. Use explicit column names, never SELECT *.
8. Use table aliases (r for reviews, v for violations, etc.).
9. For "recent" queries without a time frame, filter: created_at >= NOW() - INTERVAL '30 days'.
10. Use ILIKE for case-insensitive text matching.
11. When joining, always qualify column names with table alias.

Question: {question}

Reply with ONLY the SQL query. No explanation, no markdown fences, no backticks.
""".format(schema=_DB_SCHEMA, question="{question}")

FORMAT_ANSWER_PROMPT = """\
You are a Compliance Analytics Specialist presenting database insights to ADGM \
compliance officers.

Question asked: {question}

SQL executed:
{sql}

Results: {row_count} row(s) returned
Columns: {columns}
Data (up to 5 sample rows):
{sample_results}

Write a concise, professional 2-4 sentence response that:
- Directly answers the question with the actual numbers/values from the results
- Highlights the most significant finding or trend if multiple rows are returned
- Uses professional compliance terminology
- If zero rows were returned, clearly states that no matching records exist
- Does NOT quote the SQL or mention technical database details

Your answer:
"""
