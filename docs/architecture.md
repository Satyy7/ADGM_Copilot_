# ADGM Compliance Copilot — System Architecture

## Architecture Diagram

```mermaid
graph TD
    %% ── Styles ──────────────────────────────────────────────────────────────
    classDef user       fill:#1a1a2e,stroke:#e94560,color:#fff,font-weight:bold
    classDef frontend   fill:#16213e,stroke:#0f3460,color:#e0e0e0
    classDef api        fill:#0f3460,stroke:#533483,color:#fff
    classDef agent      fill:#533483,stroke:#e94560,color:#fff
    classDef retrieval  fill:#2d4a22,stroke:#5a9e42,color:#fff
    classDef llm        fill:#4a2522,stroke:#c0392b,color:#fff
    classDef storage    fill:#1a3a4a,stroke:#2980b9,color:#fff
    classDef decision   fill:#4a3a00,stroke:#f39c12,color:#fff

    %% ── Layer 1: User ───────────────────────────────────────────────────────
    U[("User / Browser")]:::user

    %% ── Layer 2: Frontend ───────────────────────────────────────────────────
    subgraph FE["Frontend — Next.js 14  (Port 3000)"]
        direction LR
        FE1["Dashboard"]:::frontend
        FE2["Chat"]:::frontend
        FE3["Document Review"]:::frontend
        FE4["Clause Generator"]:::frontend
        FE5["Analytics"]:::frontend
        FE6["Case Search"]:::frontend
    end

    %% ── Layer 3: API ────────────────────────────────────────────────────────
    subgraph API["API Layer — FastAPI  (Port 8000)  |  CORS Middleware"]
        direction LR
        R1["/api/v1/chat"]:::api
        R2["/api/v1/reviews/analyze"]:::api
        R3["/api/v1/generated-clauses/generate"]:::api
        R4["/api/v1/analytics/query"]:::api
        R5["/api/v1/cases/search"]:::api
        R6["/health  +  /api/v1/cache"]:::api
    end

    %% ── Layer 4: Agent Orchestration ────────────────────────────────────────
    subgraph ORCH["Agent Orchestration — LangGraph StateGraph"]
        direction TB
        IR["route_intent\n(Intent Router)"]:::decision

        subgraph CHAT["Compliance Chat Pipeline"]
            direction LR
            C1["retrieve"]:::agent --> C2["crag_evaluate"]:::agent
            C2 -->|relevant / ambiguous| C3["self_check_evidence"]:::agent
            C2 -->|irrelevant| C4["rewrite_and_retrieve"]:::agent --> C3
            C3 --> C5["generate"]:::agent --> C6["self_grade_answer"]:::agent
        end

        subgraph REV["Review Pipeline (6 Agents)"]
            direction LR
            RV1["classify_document"]:::agent --> RV2["extract_clauses"]:::agent
            RV2 --> RV3["retrieve_regulations"]:::agent --> RV4["detect_violations"]:::agent
            RV4 --> RV5["analyse_gaps"]:::agent --> RV6["generate_report"]:::agent
        end

        subgraph CLAUSE["Clause Sub-Graph (3 Nodes)"]
            direction LR
            CL1["parse_request"]:::agent --> CL2["retrieve_context"]:::agent --> CL3["generate_clause"]:::agent
        end

        subgraph ANALYTICS["Analytics Sub-Graph (Text2SQL)"]
            direction LR
            AN1["generate_sql"]:::agent --> AN2["validate_sql"]:::agent
            AN2 --> AN3["execute_sql"]:::agent --> AN4["format_answer"]:::agent
        end

        IR -->|compliance_chat| C1
        IR -->|compliance_review| RV1
        IR -->|clause_generation| CL1
        IR -->|analytics| AN1
    end

    %% ── Layer 5: Retrieval Stack ────────────────────────────────────────────
    subgraph RET["Retrieval Stack"]
        direction TB
        CACHE["CachedRetriever\n(Redis · 30 min TTL)"]:::retrieval
        HYDE["HyDERetriever\n(Hypothetical Doc Expansion)"]:::retrieval
        RERANK["RerankedRetriever\n(LLM Listwise Re-ranking)"]:::retrieval
        HYBRID["HybridRetriever\n(Reciprocal Rank Fusion)"]:::retrieval
        DENSE["QdrantRetriever\n(Dense · Gemini Embeddings)"]:::retrieval
        SPARSE["BM25Retriever\n(Sparse · TF-IDF)"]:::retrieval

        CACHE --> HYDE --> RERANK --> HYBRID
        HYBRID --> DENSE
        HYBRID --> SPARSE
    end

    %% ── Layer 6: LLM Providers ──────────────────────────────────────────────
    subgraph LLM["LLM Providers"]
        direction LR
        G["Gemini 2.0 Flash\n(Primary)"]:::llm
        GQ["Groq llama-3.3-70b-versatile\n(Automatic Fallback)"]:::llm
        G -->|on failure| GQ
    end

    %% ── Layer 7: Storage ────────────────────────────────────────────────────
    subgraph STORE["Storage Layer"]
        direction TB
        subgraph QD["Qdrant Vector DB (5 Collections)"]
            direction LR
            Q1["regulations"]:::storage
            Q2["guidance"]:::storage
            Q3["templates"]:::storage
            Q4["checklists"]:::storage
            Q5["historical_reviews"]:::storage
        end
        subgraph PG["PostgreSQL (8 Tables)"]
            direction LR
            P1["users"]:::storage
            P2["documents"]:::storage
            P3["reviews"]:::storage
            P4["violations"]:::storage
            P5["recommendations"]:::storage
            P6["generated_clauses"]:::storage
            P7["query_logs"]:::storage
            P8["audit_logs"]:::storage
        end
        RC["Redis Cache\n(Embeddings · 7d TTL\nGeneration · 1h TTL\nRetrieval · 30m TTL)"]:::storage
    end

    %% ── Connections between layers ──────────────────────────────────────────
    U --> FE
    FE -->|"proxy /api/backend/* → :8000/api/v1/*"| API
    R1 --> IR
    R2 --> RV1
    R3 --> CL1
    R4 --> AN1
    R5 --> RET

    C1 --> CACHE
    RV3 --> CACHE
    CL2 --> CACHE

    C5 --> LLM
    RV1 --> LLM
    RV2 --> LLM
    RV4 --> LLM
    RV5 --> LLM
    RV6 --> LLM
    CL1 --> LLM
    CL3 --> LLM
    AN1 --> LLM
    AN4 --> LLM

    DENSE --> QD
    AN3 --> PG
    C6 --> PG
    CL3 --> PG
    RC -.->|"cache layer"| CACHE
    RC -.->|"cache layer"| LLM

    %% ── Legend ──────────────────────────────────────────────────────────────
    subgraph LEGEND["Legend"]
        L1["User / Browser"]:::user
        L2["Frontend Component"]:::frontend
        L3["API Route"]:::api
        L4["Agent / Node"]:::agent
        L5["Retrieval Service"]:::retrieval
        L6["LLM Provider"]:::llm
        L7["Storage System"]:::storage
        L8["Decision Node"]:::decision
    end
```

---

## Layer Descriptions

### Layer 1 — User

The end user accesses the platform through any modern browser. The frontend is the sole entry point; no backend services are exposed directly to the internet in the standard deployment.

---

### Layer 2 — Frontend (Next.js 14, Port 3000)

Built with Next.js 14 (App Router), TypeScript, Tailwind CSS, and shadcn/ui. Provides six purpose-built pages:

| Page | Route | Purpose |
|---|---|---|
| Dashboard | `/` | System health, recent activity, key metrics |
| Chat | `/chat` | Interactive compliance Q&A with source citations |
| Document Review | `/review` | PDF/DOCX upload triggering the 6-agent review pipeline |
| Clause Generator | `/clauses` | Natural language clause drafting with regulation citations |
| Analytics | `/analytics` | Natural language Text2SQL compliance reporting |
| Case Search | `/cases` | Semantic search over historical review database |

All API calls are proxied through the Next.js rewrite rule:

```
/api/backend/:path*  →  http://localhost:8000/api/v1/:path*
```

This means the browser never makes cross-origin requests directly to the FastAPI backend.

---

### Layer 3 — API Layer (FastAPI, Port 8000)

A FastAPI application serving as the interface between the frontend and all backend intelligence. CORS middleware is configured to allow requests from `http://localhost:3000`.

**Route Groups:**

| Route Group | Prefix | Description |
|---|---|---|
| Compliance Chat | `POST /api/v1/chat` | LangGraph intent-router entry point |
| Document Review | `POST /api/v1/reviews/analyze` | 6-agent compliance review pipeline |
| Clause Generator | `POST /api/v1/generated-clauses/generate` | AI clause drafting |
| Analytics | `POST /api/v1/analytics/query` | Text2SQL natural language analytics |
| Case Search | `POST /api/v1/cases/search` | Historical case similarity search |
| Health | `GET /health` | Infrastructure health check (Postgres, Qdrant, Redis) |
| Cache | `GET/DELETE /api/v1/cache` | Cache statistics and manual flush |

CRUD endpoints for `users`, `documents`, `violations`, `recommendations`, `audit_logs`, `query_logs`, and `generated_clauses` are also registered.

---

### Layer 4 — Agent Orchestration (LangGraph StateGraph)

The intelligence backbone of the platform. A LangGraph `StateGraph` compiles four capability pipelines into a single unified workflow. An intent-routing node (`route_intent`) classifies every incoming query using an LLM call and dispatches it to the correct sub-graph.

**Compliance Chat Pipeline (Phases 8, 14, 15)**

```
retrieve → crag_evaluate → [rewrite_and_retrieve →] self_check_evidence → generate → self_grade_answer
```

- `retrieve`: Calls the full retrieval stack to fetch top-K regulation chunks.
- `crag_evaluate`: Corrective RAG gate — scores retrieved context as relevant, ambiguous, or irrelevant.
- `rewrite_and_retrieve`: If context is irrelevant, rewrites the query and re-retrieves.
- `self_check_evidence`: Pre-generation self-RAG check — verifies evidence supports the question.
- `generate`: Gemini/Groq generates a cited, regulation-grounded answer.
- `self_grade_answer`: Post-generation self-RAG check — grades answer groundedness.

**Review Pipeline — 6 Agents (Phase 9)**

```
classify_document → extract_clauses → retrieve_regulations → detect_violations → analyse_gaps → generate_report
```

A strictly sequential pipeline where each agent builds on prior agent output to produce a scored compliance report with violations and recommendations.

**Clause Sub-Graph (Phase 10)**

```
parse_request → retrieve_context → generate_clause
```

Parses the user's plain-English clause request, retrieves matching ADGM regulations and templates, then generates a numbered, citation-backed legal clause.

**Analytics Sub-Graph — Text2SQL (Phase 12)**

```
generate_sql → validate_sql → execute_sql → format_answer
```

Converts natural language analytics questions into safe, validated SQL queries, executes them against PostgreSQL, and formats the results as a professional compliance narrative. Supports a human-in-the-loop preview mode.

---

### Layer 5 — Retrieval Stack

A layered retrieval architecture assembled from composable services. Each layer wraps the one beneath it, adding capability without changing the shared `Retriever` protocol interface.

```
CachedRetriever (Redis · 30 min TTL)
  └── HyDERetriever (Hypothetical Document Embedding)
        └── RerankedRetriever (LLM Listwise Re-ranking · candidate pool = 20)
              └── HybridRetriever (Reciprocal Rank Fusion)
                    ├── QdrantRetriever (Dense · Gemini embedding-001)
                    └── BM25Retriever (Sparse · rank-bm25)
```

| Component | Phase | Role |
|---|---|---|
| `QdrantRetriever` | Phase 5 | Semantic dense search across Qdrant collections |
| `BM25Retriever` | Phase 6 | Keyword-based sparse search using rank-bm25 |
| `HybridRetriever` | Phase 6 | Reciprocal Rank Fusion (RRF) merges dense + sparse results |
| `RerankedRetriever` | Phase 7 | LLM listwise re-ranker selects the best K from top-20 candidates |
| `HyDERetriever` | Phase 13 | Generates a hypothetical answer, embeds it for expanded query coverage |
| `CachedRetriever` | Phase 16 | Redis cache at the outermost layer; short-circuits the full stack on hits |

---

### Layer 6 — LLM Providers

**Primary: Google Gemini 2.0 Flash** (`gemini-2.0-flash`)
Used for all generation tasks: compliance answers, document classification, clause drafting, SQL generation, violation detection, CRAG evaluation, self-RAG grading, and LLM-based re-ranking.

**Embeddings: Gemini Embedding Model** (`gemini-embedding-001`)
Used exclusively for creating vector embeddings during ingestion and at query time. The embedding model is not subject to the Groq fallback.

**Fallback: Groq llama-3.3-70b-versatile** (`llama-3.3-70b-versatile`)
Activated automatically when Gemini returns any error (rate limit, quota exhaustion, API failure). The `GeminiClient` class handles the fallback transparently — all agent nodes see a single client interface.

---

### Layer 7 — Storage Layer

**Qdrant Vector Database (5 Collections)**

| Collection | Contents |
|---|---|
| `regulations` | Full text of ADGM regulations (FSMR, COBS, PRU, etc.) chunked and embedded |
| `guidance` | ADGM regulatory guidance notices and FAQs |
| `templates` | Standard-form templates for AoA, MoA, employment contracts, UBO declarations |
| `checklists` | Compliance checklists for licensing, AML/CFT, corporate governance |
| `historical_reviews` | Embeddings of past compliance review reports for similarity search |

**PostgreSQL (8 Tables)**

`users`, `documents`, `reviews`, `violations`, `recommendations`, `generated_clauses`, `query_logs`, `audit_logs`

**Redis Cache**

Three-tier caching strategy:
- **Embeddings**: 7-day TTL — avoids redundant calls to the Gemini embedding API
- **LLM generation**: 1-hour TTL — caches compliance answers and generated text
- **Retrieval results**: 30-minute TTL — short-circuits the entire retrieval stack on repeated queries
