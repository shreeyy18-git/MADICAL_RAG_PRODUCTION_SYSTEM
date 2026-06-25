# Medical RAG API — Backend

FastAPI-based backend for the Medical RAG system. Runs on Render free tier (512MB RAM, 14 Python packages).

## Stack

| Component | Service | Notes |
|-----------|---------|-------|
| Framework | FastAPI + Uvicorn | CORS configurable via `CORS_ORIGINS` env var |
| Auth | Supabase Auth | JWKS ES256 verification, no shared secret needed |
| Database | Supabase Postgres | 5 tables: conversations, messages, documents, memory_facts, profiles |
| Vector Store | Qdrant Cloud | 3 collections: medical_chunks_local, medical_rag, mem0migrations |
| Rate Limiting | Upstash Redis | REST-based (no redis-py needed), 10 req/min/user |
| Primary LLM | Groq (Llama 3.3 70B) | Via direct httpx, no SDK |
| Fallback LLM | Gemini Flash 2.0 | Via direct httpx, no SDK |
| Cloud Embeddings | Hugging Face Inference API | `all-MiniLM-L6-v2`, 384-dim, no PyTorch needed |
| BM25 | rank_bm25 | In-memory, loaded from Qdrant chunks |
| Observability | Langfuse v4 | OpenTelemetry-based, traces grouped by session_id |
| Response Cache | Upstash Redis | 24h TTL, keyed by user + query + conversation_id |

## Requirements (14 packages)

```
fastapi, uvicorn, python-multipart, pydantic, pydantic-settings,
httpx, PyJWT, qdrant-client, supabase, rank-bm25, PyMuPDF,
langfuse, langchain-huggingface, litellm
```

No PyTorch, no transformers, no sentence-transformers — all embeddings go through Hugging Face Inference API.

## Quick Start

```bash
pip install -r requirements.txt
cp .env.example .env   # fill in all values
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

## Health Check

```bash
curl http://localhost:8000/health
```

Returns `status: "ok"` plus all active feature flags including `huggingface_embeddings` and `local_embeddings`.

## API Routes

### Auth (`/auth`)
- `POST /auth/register` — Create user via Supabase Admin API (no email confirmation)
- `POST /auth/login` — Authenticate, returns JWT

### Chat (`/chat`)
- `POST /chat` — Non-streaming RAG with structured response (Overview / Key Points / Details / Sources)
- `POST /chat/stream` — SSE streaming, yields `data: {"type":"token","content":"..."}` events then metadata
- `GET /chat/history` — List conversations with message counts
- `GET /chat/history/{id}` — Get messages for a conversation
- `DELETE /chat/history/{id}` — Delete conversation + messages

### Profile (`/api/profile`)
- `GET /api/profile` — Get user profile (display_name, age, phone, older_disease)
- `PUT /api/profile` — Update profile (sets `updated_at`)

### Admin (`/admin`)
- `POST /admin/ingest` — Upload + chunk + embed PDF (admin-only, gated by `ADMIN_USER_IDS`)

## RAG Workflow

Sequential pipeline (no external workflow engine dependency):

```
User Query
  → Cache Check (Upstash)
  → Rate Limit Check (Upstash)
  → Emergency Guardrail (keyword match)
  → Query Rewrite (Groq LLM)
  → Memory Retrieval (Supabase)
  → Hybrid Search (Qdrant vector + BM25 keyword)
  → LLM Reranker (Groq scoring)
  → Session Context (cross-session embedding similarity)
  → LLM Generation (Groq primary, Gemini fallback)
    → Structured prompt produces: Overview / Key Points / Details / Sources
  → Safety Guardrail (LLM check)
  → History Store (Supabase)
  → Cache Store (Upstash)
  → Memory Extraction (Supabase)
  → Langfuse Trace
```

## Streaming

The `/chat/stream` endpoint yields Server-Sent Events:

```
data: {"type":"token","content":"## Overview\nDiabetes is..."}
data: {"type":"token","content":" a chronic condition..."}
data: {"type":"token","content":"\n\n## Key Points\n- ..."}
data: {"type":"metadata","conversation_id":"...","sources":[...],"model":"groq/llama-3.3-70b-versatile","flagged_emergency":false}
```

The LLM is prompted to return a structured markdown response with `## Overview`, `## Key Points`, `## Details`, and `## Sources` sections, plus an educational disclaimer.

## Project Layout

```
app/
  main.py                   FastAPI entry + CORS (reads CORS_ORIGINS env var)
  config.py                 Pydantic Settings + all feature flags
  core/security.py          JWKS JWT verification
  core/logging.py           Logging setup
  models/schemas.py         Pydantic request/response models
  api/routes/
    health.py               GET /health
    auth.py                 POST /auth/register, /auth/login
    chat.py                 POST /chat, /chat/stream + history CRUD
    documents.py            POST /documents/upload, /admin/ingest
    profile.py              GET/PUT /api/profile
  services/
    supabase_client.py      Supabase Postgres + Storage helpers
    embeddings.py           HF cloud → Gemini fallback (no PyTorch)
    llm.py                  Groq → Gemini → LiteLLM chain + streaming
    graph.py                Sequential RAG workflow orchestrator
    retrieval.py            Hybrid search (vector + BM25) orchestration
    vector_store.py         Qdrant client
    keyword_search.py       BM25 via rank_bm25
    reranker.py             LLM-based result scoring
    query_rewrite.py        Context-aware query reformulation
    memory.py               Long-term fact extraction + retrieval
    rate_limit.py           Upstash Redis rate limiting
    guardrails.py           Emergency keyword detection + safety LLM check
    observability.py        Langfuse v4 tracing (flush on shutdown)
    cache.py                Upstash Redis response cache
    chunking.py             PyMuPDF text extraction + chunking
  db/supabase_schema.sql    Full DDL + RLS policies
  render.yaml               Render Blueprint (38 env vars, free plan)
  .env.example              All config keys documented
scripts/
  ingest_documents.py       Bulk PDF ingestion CLI
  evaluate_ragas.py         RAGAS offline evaluation
```

## Configuration

All config via `.env` (see `.env.example`). Key env vars:

| Variable | Description |
|----------|-------------|
| `SUPABASE_URL` | Supabase project URL |
| `SUPABASE_SERVICE_KEY` | service_role key (server-side only) |
| `QDRANT_URL` / `QDRANT_API_KEY` | Qdrant Cloud cluster |
| `GROQ_API_KEY` | Groq console key |
| `GEMINI_API_KEY` | Google AI Studio key |
| `HUGGINGFACEHUB_API_TOKEN` | HF token for Inference API |
| `UPSTASH_REDIS_REST_URL` / `UPSTASH_REDIS_REST_TOKEN` | Upstash credentials |
| `LANGFUSE_PUBLIC_KEY` / `LANGFUSE_SECRET_KEY` | Langfuse project keys |
| `CORS_ORIGINS` | Comma-separated allowed origins (set to Vercel URL in production) |
| `ADMIN_USER_IDS` | Comma-separated Supabase user IDs allowed to ingest |

## Feature Flags

All `ENABLE_*` flags default to `false`. Set to `true` to enable. Current production state: all enabled except `ENABLE_LOCAL_EMBEDDINGS` and `ENABLE_QDRANT_MEMORY`.

## Deployment

See `render.yaml` for the complete Render Blueprint with all 38 env vars. Build command: `pip install -r requirements.txt`. Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`. Health check path: `/health`.

## Component Verification

```
  PASS  Supabase         — conversations table accessible
  PASS  Qdrant           — 3 collections
  PASS  Redis (Upstash)  — rate limiting operational
  PASS  BM25             — 5 results, top score 5.296
  PASS  Hybrid search    — 5 chunks, top score 0.081
  PASS  Embeddings       — 384-dim vectors via HF cloud
  PASS  Langfuse         — initialized and tracing
  PASS  Guardrails       — emergency + safety detection
  PASS  Query rewrite    — context-aware rewriting
  PASS  Chunking         — PDF text splitting
```
