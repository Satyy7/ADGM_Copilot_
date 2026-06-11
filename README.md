# ADGM Compliance Copilot

![Python](https://img.shields.io/badge/Python-3.12-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-green)
![Next.js](https://img.shields.io/badge/Next.js-14-black)
![LangGraph](https://img.shields.io/badge/LangGraph-purple)
![License](https://img.shields.io/badge/License-MIT-yellow)

AI-powered compliance intelligence platform for organizations operating within the Abu Dhabi Global Market (ADGM).

---

## Overview

ADGM Compliance Copilot helps compliance teams, legal professionals, and business owners work with ADGM regulations more efficiently.

Instead of manually searching through regulations, guidance notices, and templates, users can ask questions in natural language, review legal documents, generate compliance-focused clauses, and analyze historical compliance data.

The platform combines Retrieval-Augmented Generation (RAG), hybrid retrieval, LangGraph workflows, and regulatory knowledge retrieval to provide grounded answers backed by source citations.

---

## Why I Built This

Compliance work is heavily document-driven and often requires navigating large volumes of regulations and guidance material.

This project started as an experiment to see whether modern RAG techniques and agent-based workflows could simplify regulatory research and document review while maintaining traceability and transparency.

Over time it evolved into a complete compliance intelligence platform with support for:

- Compliance Q&A
- Document review
- Clause generation
- Compliance analytics
- Historical case search

---

## Features

### Compliance Chat

Ask questions about ADGM regulations and receive citation-backed responses grounded in retrieved regulatory documents.

### Document Review

Upload PDF or DOCX files and receive:

- Compliance score
- Detected violations
- Gap analysis
- Recommendations
- Executive summary

### Clause Generator

Generate ADGM-compliant clauses using regulations and standard document templates.

### Compliance Analytics

Query compliance data using natural language and generate insights through a secure Text-to-SQL workflow.

### Historical Case Search

Search previous compliance reviews using semantic similarity to identify patterns and similar cases.

---

## Technology Stack

### Frontend

- Next.js 14
- TypeScript
- Tailwind CSS
- shadcn/ui

### Backend

- FastAPI
- Python 3.12
- SQLAlchemy
- Pydantic

### AI & Retrieval

- LangGraph
- Gemini 2.0 Flash
- Gemini Embeddings
- Groq (Fallback LLM)
- Hybrid Search
- BM25
- HyDE
- CRAG
- Self-RAG

### Databases

- PostgreSQL
- Qdrant
- Redis

### Infrastructure

- Docker Compose
- uv

---

## Project Structure

```text
ADGM_Compliance_Copilot
│
├── backend
│   ├── app
│   │   ├── agent
│   │   ├── api
│   │   ├── core
│   │   ├── db
│   │   ├── models
│   │   ├── repositories
│   │   ├── schemas
│   │   └── services
│   └── main.py
│
├── nextjs-frontend
│   ├── src
│   │   ├── app
│   │   ├── components
│   │   ├── lib
│   │   └── types
│
├── data
├── docs
├── scripts
├── tests
├── docker
├── pyproject.toml
└── uv.lock
```

---

## Getting Started

### Prerequisites

- Python 3.12+
- Node.js 20+
- Docker
- Git
- uv

### Required API Keys

- Gemini API Key
- Groq API Key

---

## Installation

### Clone Repository

```bash
git clone https://github.com/your-username/adgm-compliance-copilot.git
cd adgm-compliance-copilot
```

### Install Backend Dependencies

```bash
uv sync
```

### Install Frontend Dependencies

```bash
cd nextjs-frontend
npm install
cd ..
```

### Configure Environment Variables

Create a `.env` file:

```env
GEMINI_API_KEY=your_key
GROQ_API_KEY=your_key

POSTGRES_HOST=localhost
POSTGRES_PORT=5432

QDRANT_HOST=localhost
QDRANT_PORT=6333

REDIS_HOST=localhost
REDIS_PORT=6379
```

---

## Start Infrastructure

```bash
docker compose -f docker/docker-compose.yml up -d
```

This starts:

- PostgreSQL
- Qdrant
- Redis

---

## Run Database Migrations

```bash
alembic upgrade head
```

---

## Ingest Knowledge Base

```bash
python scripts/ingest_knowledge_base.py
```

---

## Run the Application

### Backend

```bash
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

### Frontend

```bash
cd nextjs-frontend
npm run dev
```

---

## Local URLs

Frontend

```text
http://localhost:3000
```

Backend

```text
http://localhost:8000
```

Swagger Docs

```text
http://localhost:8000/docs
```

---

## API Endpoints

| Method | Endpoint | Purpose |
|----------|----------|----------|
| POST | `/api/v1/chat` | Compliance Q&A |
| POST | `/api/v1/reviews/analyze` | Document Review |
| POST | `/api/v1/generated-clauses/generate` | Clause Generation |
| POST | `/api/v1/analytics/query` | Compliance Analytics |
| POST | `/api/v1/cases/search` | Historical Case Search |

---

## Documentation

Detailed architecture documentation is available in:

```text
docs/architecture.md
```

---

## Current Limitations

- Generated clauses should always be reviewed by legal professionals.
- Retrieval quality depends on document chunking and indexing strategy.
- Regulatory updates require periodic re-indexing.
- Text-to-SQL workflows currently support read-only operations.
- Complex compliance scenarios may require multiple retrieval cycles.

---

## Future Improvements

- Multi-jurisdiction compliance support
- Regulatory change monitoring
- Agent memory
- Human approval dashboards
- Enterprise SSO
- Multi-document review workflows
- Advanced compliance analytics

---

## License

MIT License

This project is intended for educational, research, and compliance-assistance purposes.

Users remain responsible for validating legal interpretations and compliance decisions before relying on generated outputs.
