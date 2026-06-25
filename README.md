# Medical RAG Production

A production-grade Medical Retrieval-Augmented Generation (RAG) system with admin document ingestion, user chat, streaming responses, and zero-cost free-tier infrastructure. Deployed on Render (backend) + Vercel (frontend).

## Architecture

```
Frontend (React/Vite) ──HTTP──> Backend (FastAPI)
                │                       │
           Vercel (free)           Render (free)
                                     │
         ┌───────────────────────────┼───────────────────────────┐
         ▼                           ▼                           ▼
    Supabase                      Qdrant                    Upstash Redis
 (Auth, DB, Storage)         (Vector store)              (Rate limiting + cache)
         │                           │
         ▼                           ▼
    Groq API                    Hugging Face
  (Primary LLM)              Inference API
         │                 (Cloud embeddings)
         ▼
    Gemini Flash
  (Fallback LLM)
         │
         ▼
    Langfuse Hobby
  (Observability)
```

## Stack

| Component | Service | Tier |
|-----------|---------|------|
| Frontend | React + Vite | Vercel (free) |
| Backend | FastAPI + Uvicorn | Render (free) |
| Auth + DB + Storage | Supabase | Free |
| Vector Store | Qdrant Cloud | Free |
| Rate Limiting + Cache | Upstash Redis | Free |
| Primary LLM | Groq (Llama 3.3 70B) | Free |
| Fallback LLM | Gemini Flash 2.0 | Free |
| Cloud Embeddings | Hugging Face Inference API | Free |
| BM25 Search | In-memory (rank_bm25) | Free |
| Observability | Langfuse Hobby | Free |

## Features

- **PDF Ingestion**: Admin-only upload/ingest pipeline (PyMuPDF chunking → HF embeddings → Qdrant)
- **Hybrid Search**: Vector (Qdrant) + BM25 (keyword) combined retrieval
- **LLM Reranker**: Query-aware result re-scoring via Groq
- **Query Rewrite**: Context-aware question reformulation
- **Long-term Memory**: Fact extraction and retrieval across sessions
- **Cross-session History**: Embedding similarity-based past conversation recall
- **Streaming Responses**: SSE-based token-by-token generation
- **Guardrails**: Emergency keyword detection + post-generation safety check
- **Rate Limiting**: Per-user via Upstash Redis (10 req/min)
- **Response Caching**: Identical query dedup (24h TTL via Upstash)
- **Observability**: Full Langfuse tracing with session grouping
- **JWT Auth**: Supabase Auth with JWKS ES256 verification
- **User Profile**: Name, age, conditions stored and injected into RAG context
- **Structured Answers**: LLM prompted to return Overview → Key Points → Details → Sources sections
- **Responsive UI**: Mobile-friendly with 3 breakpoint levels

## Prerequisites

- Python 3.12+
- Node.js 18+
- Supabase project (free tier)
- Qdrant Cloud cluster (free tier)
- Groq API key (free at console.groq.com)
- Gemini API key (free at aistudio.google.com)
- Hugging Face token (free at huggingface.co/settings/tokens)
- Upstash Redis database (free)
- Langfuse project (free Hobby tier)

## Quick Start

### Backend

```bash
cd backend
python -m venv venv
# source venv/bin/activate  (Linux)
# venv\Scripts\activate     (Windows)
pip install -r requirements.txt
cp .env.example .env
# Fill in all API keys and URLs
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

### Verify

```bash
curl http://localhost:8000/health
# {"status":"ok","phase_flags":{"hybrid_search":true,...,"huggingface_embeddings":true,"local_embeddings":false}}
```

## Project Structure

```
backend/
  app/
    main.py              FastAPI app entry point (+ CORS from env var)
    config.py            Settings + feature flags
    core/security.py     JWT verification (JWKS ES256)
    api/routes/
      health.py, auth.py, chat.py, documents.py, profile.py
    services/
      supabase_client.py, embeddings.py (HF cloud / Gemini fallback)
      llm.py (Groq/Gemini/LiteLLM + streaming), graph.py (workflow)
      retrieval.py, vector_store.py, keyword_search.py (BM25)
      reranker.py, query_rewrite.py, memory.py, rate_limit.py
      guardrails.py, observability.py, cache.py, chunking.py
    db/supabase_schema.sql
    render.yaml           Render Blueprint (38 env vars)
    .env.example
  scripts/
    ingest_documents.py   Bulk PDF ingestion
frontend/
  src/
    pages/                Landing, Login, Dashboard, Chat, History, Profile
    components/           ProtectedRoute, Sidebar, ChatBubble, Loader
    services/             auth.js, api.js (VITE_API_URL aware)
  vercel.json             SPA rewrite rules
```

## API Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/auth/register` | No | Register new user |
| POST | `/auth/login` | No | Login, returns JWT |
| GET | `/health` | No | Health check + feature flags |
| POST | `/chat` | JWT | Non-streaming chat |
| POST | `/chat/stream` | JWT | SSE streaming chat |
| GET | `/chat/history` | JWT | List conversations |
| GET | `/chat/history/{id}` | JWT | Get conversation messages |
| DELETE | `/chat/history/{id}` | JWT | Delete conversation |
| GET | `/api/profile` | JWT | Get user profile |
| PUT | `/api/profile` | JWT | Update user profile |
| POST | `/admin/ingest` | JWT+Admin | Ingest PDF documents |

## Deployment

### Backend → Render

1. Push repo to GitHub
2. In Render dashboard: New Web Service → connect repo → use `backend/render.yaml` Blueprint
3. Fill all `sync: false` secrets (Supabase, Qdrant, Groq, Gemini, HF, Upstash, Langfuse keys)
4. Set `CORS_ORIGINS` to `https://your-app.vercel.app`
5. Free tier: 512MB RAM, spins down after 15 min idle (~30s cold start)

### Frontend → Vercel

1. Import repo → Root Directory: `frontend`
2. Framework preset: Vite
3. Environment variable: `VITE_API_URL` = `https://your-app.onrender.com`
4. `vercel.json` handles SPA routing automatically

## Feature Flags

All configured via `.env`. Health endpoint reports active flags.

| Flag | Default | Purpose |
|------|---------|---------|
| `ENABLE_HYBRID_SEARCH` | true | Vector + BM25 retrieval |
| `ENABLE_QUERY_REWRITE` | true | LLM query rewriting |
| `ENABLE_LLM_RERANK` | true | LLM result re-scoring |
| `ENABLE_LONG_TERM_MEMORY` | true | Cross-session facts |
| `ENABLE_RATE_LIMITING` | true | Upstash per-user limits |
| `ENABLE_GUARDRAILS` | true | Emergency + safety checks |
| `ENABLE_OBSERVABILITY` | true | Langfuse tracing |
| `ENABLE_RESPONSE_CACHE` | true | Cache identical queries |
| `ENABLE_LANGGRAPH` | true | Workflow orchestrator |
| `ENABLE_CROSS_SESSION_HISTORY` | true | Past conversation recall |
| `ENABLE_HUGGINGFACE_EMBEDDINGS` | true | Cloud embeddings (HF Inference API) |
| `ENABLE_LOCAL_EMBEDDINGS` | false | Local PyTorch (not recommended on free tier) |
| `ENABLE_QDRANT_MEMORY` | false | Qdrant-based memory store |

## Design Decisions

- **Hugging Face cloud embeddings** instead of local PyTorch — avoids 800MB torch install, stays within Render's 512MB RAM. Uses `sentence-transformers/all-MiniLM-L6-v2` (384-dim) via HF Inference API.
- **Groq primary, Gemini fallback** — both free, both fast. LiteLLM available as optional gateway.
- **JWKS auth** instead of shared JWT secret — works with Supabase's default ES256 signing keys.
- **Custom guardrails** instead of `guardrails-ai` library — lighter weight, no extra dependencies.
- **Manual workflow** instead of LangGraph StateGraph — same sequential logic, no dependency on langgraph at runtime.
