"""Text2SQL analytics prompts — Phase 12.

Two prompts:
  SQL_GENERATION_PROMPT   — converts natural language to a safe SELECT statement
  SQL_REPAIR_PROMPT       — fixes a SQL query that failed with a PostgreSQL error
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

FOREIGN KEYS (the ONLY valid JOIN conditions):
  documents.user_id        → users.id
  reviews.document_id      → documents.id
  reviews.user_id          → users.id
  violations.review_id     → reviews.id
  recommendations.review_id → reviews.id
  recommendations.violation_id → violations.id
  generated_clauses.user_id → users.id
  audit_logs.user_id       → users.id
  query_logs.user_id       → users.id

NOTE: generated_clauses has NO foreign key to documents or reviews.
      Clause queries are standalone — do NOT join generated_clauses with
      documents or reviews unless going through users.
"""

SQL_GENERATION_PROMPT = """\
You are an ADGM Compliance Database Analyst. Convert the compliance analytics \
question into a precise, read-only SQL query for PostgreSQL.

DATABASE SCHEMA:
{schema}

RULES:
1.  Only SELECT statements. NEVER use INSERT, UPDATE, DELETE, DROP, ALTER, \
TRUNCATE, CREATE, EXEC, EXECUTE, CALL, GRANT, REVOKE.
2.  Cast UUIDs to text: CAST(id AS TEXT) AS id.
3.  Format timestamps: TO_CHAR(created_at, 'YYYY-MM-DD HH24:MI') AS created_at.
4.  Cast NUMERIC to FLOAT where needed: CAST(compliance_score AS FLOAT).
5.  For aggregation queries (COUNT/SUM/AVG/MIN/MAX) do NOT add LIMIT.
6.  For all other queries add LIMIT 50 unless the question asks for more.
7.  Use explicit column names, never SELECT *.
8.  Use table aliases (r for reviews, v for violations, gc for generated_clauses, etc.).
9.  ONLY add a date filter when the question explicitly uses time words such as \
"recent", "today", "this week", "this month", "last N days/weeks/months". \
For ALL other questions return data from every time period — do NOT add any \
created_at or date filter unless the user asked for one.
10. Use ILIKE for case-insensitive text matching.
11. When joining, always qualify column names with table alias.
12. GROUP BY rule — CRITICAL: every column in the SELECT list that is NOT \
inside an aggregate function (COUNT, SUM, AVG, MIN, MAX) MUST also appear \
in the GROUP BY clause. Never put a bare column in SELECT and omit it from \
GROUP BY. Example: SELECT a, b, COUNT(*) ... GROUP BY a, b — both a and b \
must be in GROUP BY.
13. JOIN rule — CRITICAL: only join tables on the foreign key relationships \
listed in the schema above. Never invent a join condition that does not \
correspond to an actual foreign key.

Question: {question}

Reply with ONLY the SQL query. No explanation, no markdown fences, no backticks.
""".format(schema=_DB_SCHEMA, question="{question}")


SQL_REPAIR_PROMPT = """\
A PostgreSQL query failed with an error. Fix it so it runs correctly.

FAILED SQL:
{sql}

ERROR MESSAGE:
{error}

DATABASE SCHEMA (foreign keys and column names for reference):
{schema}

Most common fixes needed:
- GROUP BY: add every non-aggregated SELECT column to the GROUP BY clause.
- JOIN: only join on actual foreign key columns listed in the schema.
- Column alias: do not reference a SELECT alias in the WHERE or GROUP BY — \
repeat the full expression instead.
- Cast: NUMERIC columns need CAST(col AS FLOAT) before arithmetic.

Reply with ONLY the corrected SQL query. No explanation, no markdown.
""".format(schema=_DB_SCHEMA, sql="{sql}", error="{error}")


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
