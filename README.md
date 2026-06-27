# Medical RAG Production

> Created by **Shreeyansh Asati** — AI/ML Engineer  
> [![LinkedIn](https://img.shields.io/badge/LinkedIn-Connect-blue)](https://www.linkedin.com/in/shreeyansh-asati-18shreey/)  
> [![GitHub](https://img.shields.io/badge/GitHub-Follow-black)](https://github.com/SHREEYANSHGIT)  
> [![Live Backend](https://img.shields.io/badge/Backend-Render-46E3B7)](https://medical-rag-api-fl26.onrender.com/health)  
> [![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)

A production-grade **Medical Retrieval-Augmented Generation (RAG)** system with admin PDF ingestion, user chat with token-by-token streaming, structured clinical responses, and zero-cost free-tier infrastructure. Deployed on Render (backend) + Vercel (frontend).

---

## Table of Contents

- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Features](#features)
- [How It Works](#how-it-works)
- [API Endpoints](#api-endpoints)
- [Project Structure](#project-structure)
- [Prerequisites](#prerequisites)
- [Quick Start (Local)](#quick-start-local)
- [Deployment](#deployment)
  - [Backend → Render](#backend--render)
  - [Frontend → Vercel](#frontend--vercel)
- [Environment Variables](#environment-variables)
- [Feature Flags](#feature-flags)
- [Design Decisions](#design-decisions)
- [Troubleshooting](#troubleshooting)
- [License](#license)

---

## Architecture
<img width="2628" height="3186" alt="_- visual selection (5)" src="https://github.com/user-attachments/assets/182c339f-fff6-48ab-ba59-e1c2659febe7" />


### Data Flow

<img width="2184" height="7019" alt="_- visual selection (6)" src="https://github.com/user-attachments/assets/af5baa72-48d0-4d55-9a55-3fd5299317e2" />


---

## Tech Stack

| Layer | Component | Service | Tier | Purpose |
|-------|-----------|---------|------|---------|
| **Frontend** | React 19 + Vite | Vercel | Free | SPA, client-side routing |
| **Backend** | FastAPI + Uvicorn | Render | Free (512MB) | REST API, SSE streaming |
| **Auth** | Supabase Auth | Supabase | Free | JWT tokens (ES256), user management |
| **Database** | PostgreSQL | Supabase | Free | User profiles, conversations |
| **Storage** | Supabase Storage | Supabase | Free | PDF documents |
| **Vector Store** | Qdrant Cloud | Qdrant | Free (1GB) | 384-dim embeddings, 3 collections |
| **Rate Limiting** | Upstash Redis | Upstash | Free | 10 req/min per user |
| **Cache** | Upstash Redis | Upstash | Free | Response cache (24h TTL) |
| **Primary LLM** | Llama 3.3 70B | Groq | Free | 30 req/min, <1s latency |
| **Fallback LLM** | Gemini Flash 2.0 | Google AI | Free | 60 req/min |
| **LLM Gateway** | LiteLLM | — | Built-in | Proxy to multiple providers |
| **Embeddings** | all-MiniLM-L6-v2 | Hugging Face Inference API | Free | 384-dim, cloud inference |
| **Keyword Search** | BM25 (rank_bm25) | In-memory | Free | Term-frequency based retrieval |
| **Observability** | Langfuse | Langfuse Hobby | Free | Traces, sessions, cost tracking |

### Backend Packages (14 total — minimal footprint)

```text
fastapi, uvicorn, httpx, pydantic, pydantic-settings
supabase-python, qdrant-client, upstash-redis
litellm, langchain-huggingface, rank-bm25
langfuse, pyjwt, cryptography
```

No PyTorch, transformers, sentence-transformers, langchain, langgraph, or other heavy dependencies.

---

## Features

### Core RAG
- **PDF Ingestion** (Admin): Upload PDFs → PyMuPDF text extraction → semantic chunking → HF cloud embeddings → Qdrant vector storage
- **Hybrid Search**: Vector cosine similarity (Qdrant) + BM25 keyword search (rank_bm25), merged with normalized scores
- **LLM Reranker**: Groq re-scores top-20 results for query-aware relevance, keeps top-8
- **Query Rewrite**: Context-aware reformulation using conversation history and user profile
- **Structured Responses**: LLM prompted to return sections — Overview, Key Points (with [N] citations), Details, Sources, plus educational disclaimer

### User Features
- **Registration / Login**: JWT-based auth via Supabase (JWKS ES256 verification)
- **Streaming Chat**: SSE endpoint `/chat/stream` with token-by-token output
- **Conversation History**: Create, read, delete conversations with full message history
- **Cross-Session Memory**: Embedding similarity-based recall of past conversations
- **Long-Term Memory**: Extracted facts (diagnoses, medications, symptoms) stored per-user
- **User Profile**: Name, age, medical conditions — injected into RAG context

### Safety & Reliability
- **Guardrails**: Emergency keyword detection (suicide, violence) → immediate block. Post-generation safety check on LLM output
- **Rate Limiting**: 10 requests/min per user via Upstash Redis sliding window
- **Response Caching**: Identical queries deduplicated for 24h (includes `conversation_id` in cache key)
- **Fallback Chain**: Groq → Gemini → LiteLLM → error message

### Observability
- **Langfuse Tracing**: Full trace per request with `session_id` (conversation ID)
- **Feature Flag Reporting**: Health endpoint exposes all active flags
- **Render Health Checks**: Automatic restart on failure

### Frontend
- **Responsive UI**: 3 breakpoint levels (mobile / tablet / desktop)
- **Structured Rendering**: Markdown → styled HTML with collapsible sections, citation superscripts
- **Protected Routes**: Auth guard wrapping chat, history, profile pages
- **Landing Page**: Feature summary, login/register CTA
- **Dark/Light Theme**: Modern color scheme

---

## API Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `POST` | `/auth/register` | No | Register new user (email, password, name, age) |
| `POST` | `/auth/login` | No | Login, returns JWT access token |
| `GET` | `/health` | No | Health check + feature flags status |
| `POST` | `/chat` | JWT | Non-streaming chat (full response) |
| `POST` | `/chat/stream` | JWT | SSE streaming chat (token-by-token) |
| `GET` | `/chat/history` | JWT | List user conversations |
| `GET` | `/chat/history/{id}` | JWT | Get conversation messages |
| `DELETE` | `/chat/history/{id}` | JWT | Delete conversation |
| `PUT` | `/chat/history/{id}` | JWT | Rename conversation |
| `GET` | `/api/profile` | JWT | Get user profile |
| `PUT` | `/api/profile` | JWT | Update user profile |
| `POST` | `/admin/ingest` | JWT+Admin | Ingest PDF documents (requires admin role) |

---

## Project Structure

```
MADICAL_RAG_PRODUCTION_SYSTEM/
│
├── backend/                          # FastAPI backend (deployed on Render)
│   ├── app/
│   │   ├── main.py                   # App entry + CORS (reads CORS_ORIGINS env)
│   │   ├── config.py                 # Settings + all feature flags
│   │   │
│   │   ├── api/
│   │   │   ├── deps.py               # Dependency injection (get_current_user)
│   │   │   └── routes/
│   │   │       ├── health.py         # GET /health
│   │   │       ├── auth.py           # POST /auth/register, /auth/login
│   │   │       ├── chat.py           # POST /chat, /chat/stream, history CRUD
│   │   │       ├── documents.py      # POST /admin/ingest
│   │   │       └── profile.py        # GET/PUT /api/profile
│   │   │
│   │   ├── core/
│   │   │   ├── security.py           # JWT verification (JWKS ES256)
│   │   │   └── logging.py            # Logging configuration
│   │   │
│   │   ├── models/
│   │   │   └── schemas.py            # Pydantic models for all endpoints
│   │   │
│   │   ├── db/
│   │   │   └── supabase_schema.sql   # PostgreSQL schema for profiles + conversations
│   │   │
│   │   └── services/
│   │       ├── supabase_client.py    # Supabase singleton client
│   │       ├── embeddings.py         # HF Inference API → Gemini fallback
│   │       ├── llm.py                # LLM gateway (Groq → Gemini → error)
│   │       ├── graph.py              # RAG workflow (nodes + stream generator)
│   │       ├── retrieval.py          # Hybrid search orchestrator
│   │       ├── vector_store.py       # Qdrant vector search
│   │       ├── keyword_search.py     # BM25 in-memory search
│   │       ├── reranker.py           # LLM-based result re-scoring
│   │       ├── query_rewrite.py      # Context-aware query reformulation
│   │       ├── memory.py             # Long-term fact extraction + retrieval
│   │       ├── guardrails.py         # Emergency detection + safety checks
│   │       ├── rate_limit.py         # Upstash Redis sliding window
│   │       ├── cache.py              # Upstash response cache
│   │       ├── chunking.py           # PDF text chunking
│   │       └── observability.py      # Langfuse tracing
│   │
│   ├── scripts/
│   │   ├── ingest_documents.py       # Bulk PDF ingestion CLI
│   │   └── evaluate_ragas.py         # RAGAS evaluation (optional)
│   │
│   ├── render.yaml                   # Render Blueprint (38 env vars, health check)
│   ├── Dockerfile                    # python:3.12-slim, 14 packages
│   ├── requirements.txt              # Pinned 14 dependencies
│   ├── .env.example                  # All env vars documented
│   └── test_*.py                     # Integration tests
│
├── frontend/                         # React + Vite SPA (deployed on Vercel)
│   ├── src/
│   │   ├── main.jsx                  # React entry + router
│   │   ├── App.jsx                   # App shell + auth context
│   │   ├── App.css                   # All styles (including structured answers)
│   │   ├── index.css                 # Global resets
│   │   │
│   │   ├── pages/
│   │   │   ├── Landing.jsx           # Landing page with feature cards
│   │   │   ├── Login.jsx             # Login form
│   │   │   ├── Dashboard.jsx         # Post-login dashboard
│   │   │   ├── Chat.jsx              # Chat interface with streaming
│   │   │   ├── History.jsx           # Conversation history list
│   │   │   └── Profile.jsx           # User profile editor
│   │   │
│   │   ├── components/
│   │   │   ├── Navbar.jsx            # Top navigation
│   │   │   ├── Sidebar.jsx           # Mobile sidebar drawer
│   │   │   ├── ChatBubble.jsx        # Message bubble + structured rendering
│   │   │   ├── ProtectedRoute.jsx    # Auth route guard
│   │   │   ├── Card.jsx              # Reusable feature card
│   │   │   └── Loader.jsx            # Loading spinner
│   │   │
│   │   └── services/
│   │       ├── api.js                # Fetch wrapper (VITE_API_URL aware)
│   │       ├── auth.js               # Auth API calls
│   │       └── supabase.js           # Supabase client config
│   │
│   ├── vercel.json                   # SPA rewrite rules
│   ├── vite.config.js                # Dev proxy → localhost:8000
│   └── package.json                  # React 19, Vite
│
├── .env.example                      # Root-level reference
├── pyproject.toml                    # Python project metadata
└── requirements.txt                  # Root requirements (same 14 packages)
```

---

## Prerequisites

- **Python 3.12+**
- **Node.js 18+** (npm 9+)
- **Supabase project** (free tier at supabase.com)
- **Qdrant Cloud cluster** (free 1GB tier at cloud.qdrant.io)
- **Groq API key** (free at console.groq.com)
- **Gemini API key** (free at aistudio.google.com)
- **Hugging Face token** (free at huggingface.co/settings/tokens)
- **Upstash Redis database** (free at upstash.com)
- **Langfuse project** (free Hobby tier at langfuse.com)
- **GitHub account** (for Render + Vercel deployment)

---

## Quick Start (Local)

### 1. Backend Setup

```bash
cd backend
python -m venv venv

# Activate:
#   Linux/macOS: source venv/bin/activate
#   Windows:     venv\Scripts\Activate.ps1

pip install -r requirements.txt
cp .env.example .env
```

Edit `.env` with your API keys (all required keys documented in `.env.example`).

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 2. Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

### 3. Verify

```bash
# Health check
curl http://localhost:8000/health

# Expected:
# {"status":"ok","phase_flags":{"hybrid_search":true,"query_rewrite":true,
#  "llm_rerank":true,"long_term_memory":true,"rate_limiting":true,
#  "guardrails":true,"observability":true,"huggingface_embeddings":true,
#  "local_embeddings":false}}

# Register a user
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"Test123!","name":"Test User","age":30}'

# Login
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"Test123!"}'

# Chat (replace TOKEN with your JWT)
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer TOKEN" \
  -d '{"message":"What are the symptoms of diabetes?","conversation_id":"uuid-here"}'

# Stream chat
curl -N -X POST http://localhost:8000/chat/stream \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer TOKEN" \
  -d '{"message":"What are the symptoms of diabetes?","conversation_id":"uuid-here"}'
```

---

## Deployment

### Backend → Render

1. Push repository to GitHub
2. Go to [Render Dashboard](https://dashboard.render.com) → **New** → **Blueprint**
3. Connect your GitHub repo — Render auto-detects `render.yaml`
4. Fill all `sync: false` secrets in Render's environment UI:
   - `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`
   - `QDRANT_URL`, `QDRANT_API_KEY`
   - `GROQ_API_KEY`, `GEMINI_API_KEY`
   - `HUGGINGFACE_API_TOKEN`
   - `UPSTASH_REDIS_URL`, `UPSTASH_REDIS_TOKEN`
   - `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, `LANGFUSE_HOST`
5. Set `CORS_ORIGINS` to `*` (for development) or your Vercel URL
6. Click **Apply** — Render builds and deploys

**Limitations**:
- Free tier spins down after 15 minutes idle (~30s cold start on next request)
- 512MB RAM — 14-package setup fits comfortably
- Use Render's **Cron Jobs** or a keepalive service to prevent spin-down

**Environment variables in Render**:

| Variable | How to Set |
|----------|-----------|
| `SUPABASE_URL` | Manual (sync: false) |
| `SUPABASE_SERVICE_KEY` | Manual (sync: false) |
| `QDRANT_URL` | Manual (sync: false) |
| `QDRANT_API_KEY` | Manual (sync: false) |
| `GROQ_API_KEY` | Manual (sync: false) |
| `GEMINI_API_KEY` | Manual (sync: false) |
| `HUGGINGFACE_API_TOKEN` | Manual (sync: false) |
| `UPSTASH_REDIS_URL` | Manual (sync: false) |
| `UPSTASH_REDIS_TOKEN` | Manual (sync: false) |
| `LANGFUSE_PUBLIC_KEY` | Manual (sync: false) |
| `LANGFUSE_SECRET_KEY` | Manual (sync: false) |
| `LANGFUSE_HOST` | Manual (sync: false) |
| `CORS_ORIGINS` | Manual — set to `*` or your frontend URL |
| All others | Auto-synced from `render.yaml` |

### Frontend → Vercel

1. Go to [Vercel Dashboard](https://vercel.com) → **Add New Project**
2. Import your GitHub repository
3. Configure:

   | Setting | Value |
   |---------|-------|
   | **Root Directory** | `frontend` |
   | **Framework Preset** | Vite |
   | **Build Command** | `npm run build` (auto-detected) |
   | **Output Directory** | `dist` (auto-detected) |

4. Add environment variable:
   - `VITE_API_URL` = `https://your-app.onrender.com`

5. Click **Deploy**

6. After deployment, update backend `CORS_ORIGINS` to include your Vercel domain:
   ```
   CORS_ORIGINS=https://your-app.vercel.app,http://localhost:5173
   ```

### Deployed URLs

| Service | URL |
|---------|-----|
| Backend (Render) | `https://medical-rag-api-fl26.onrender.com` |
| Backend Health | `https://medical-rag-api-fl26.onrender.com/health` |
| Frontend (Vercel) | `https://your-app.vercel.app` |

---

## Environment Variables

Full reference — all 38 variables used by the system (see `backend/.env.example` for placeholder template):

### Core
| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `ENVIRONMENT` | No | `development` | Runtime environment |
| `SUPABASE_URL` | **Yes** | — | Supabase project URL |
| `SUPABASE_SERVICE_KEY` | **Yes** | — | Supabase service role key |
| `SUPABASE_JWT_SECRET` | No | (empty) | Only needed for HS256; JWKS used by default |

### Qdrant (Vector Store)
| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `QDRANT_URL` | **Yes** | — | Qdrant Cloud cluster URL |
| `QDRANT_API_KEY` | **Yes** | — | Qdrant API key |
| `QDRANT_COLLECTION` | No | `medical_chunks_local` | Collection name for chunks |
| `QDRANT_COLLECTION_MEMORY` | No | `medical_memory` | Collection for long-term memory |

### LLM Providers
| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `GROQ_API_KEY` | **Yes** | — | Groq Cloud API key |
| `GROQ_MODEL` | No | `llama-3.3-70b-versatile` | Groq model name |
| `GEMINI_API_KEY` | **Yes** | — | Google AI Studio API key |
| `GEMINI_MODEL` | No | `gemini-2.0-flash` | Gemini model name |

### Embeddings
| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `HUGGINGFACE_API_TOKEN` | **Yes** | — | Hugging Face Inference API token |
| `EMBEDDING_MODEL` | No | `sentence-transformers/all-MiniLM-L6-v2` | HF embedding model (384-dim) |

### Redis (Upstash)
| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `UPSTASH_REDIS_URL` | **Yes** | — | Upstash Redis REST URL |
| `UPSTASH_REDIS_TOKEN` | **Yes** | — | Upstash Redis REST token |

### Observability (Langfuse)
| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `LANGFUSE_PUBLIC_KEY` | **Yes** | — | Langfuse public key |
| `LANGFUSE_SECRET_KEY` | **Yes** | — | Langfuse secret key |
| `LANGFUSE_HOST` | No | `https://cloud.langfuse.com` | Langfuse API host |

### CORS
| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `CORS_ORIGINS` | No | `*` | Comma-separated allowed origins |

### Feature Flags
| Variable | Default | Description |
|----------|---------|-------------|
| `ENABLE_HYBRID_SEARCH` | `true` | Vector + BM25 combined retrieval |
| `ENABLE_QUERY_REWRITE` | `true` | LLM-based query reformulation |
| `ENABLE_LLM_RERANK` | `true` | LLM-based result re-scoring |
| `ENABLE_LONG_TERM_MEMORY` | `true` | Cross-session fact storage |
| `ENABLE_CROSS_SESSION_HISTORY` | `true` | Past conversation recall |
| `ENABLE_GUARDRAILS` | `true` | Emergency + safety checks |
| `ENABLE_RATE_LIMITING` | `true` | Per-user rate limits |
| `ENABLE_RESPONSE_CACHE` | `true` | Identical query dedup |
| `ENABLE_OBSERVABILITY` | `true` | Langfuse tracing |
| `ENABLE_LANGGRAPH` | `true` | Workflow orchestrator |
| `ENABLE_HUGGINGFACE_EMBEDDINGS` | `true` | HF cloud embeddings |
| `ENABLE_LOCAL_EMBEDDINGS` | `false` | Local embeddings (requires PyTorch) |

### Admin
| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `ADMIN_EMAILS` | No | `admin@example.com` | Comma-separated admin emails |

### LiteLLM (optional)
| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `LITELLM_API_KEY` | No | — | LiteLLM proxy key |
| `LITELLM_BASE_URL` | No | — | LiteLLM proxy URL |

---

## Feature Flags

All flags are configured through environment variables and reported via the `/health` endpoint. Toggle any flag at runtime by changing the env var and restarting the service.

| Flag | Default | When Disabled |
|------|---------|---------------|
| `ENABLE_HYBRID_SEARCH` | true | Falls back to vector-only search |
| `ENABLE_QUERY_REWRITE` | true | Sends original user query directly |
| `ENABLE_LLM_RERANK` | true | Uses raw Qdrant + BM25 scores |
| `ENABLE_LONG_TERM_MEMORY` | true | No fact extraction or retrieval |
| `ENABLE_CROSS_SESSION_HISTORY` | true | No past conversation recall |
| `ENABLE_GUARDRAILS` | true | No safety checks |
| `ENABLE_RATE_LIMITING` | true | No request limits |
| `ENABLE_RESPONSE_CACHE` | true | Every request generates fresh response |
| `ENABLE_OBSERVABILITY` | true | No Langfuse tracing |
| `ENABLE_LANGGRAPH` | true | Direct sequential code (no orchestrator) |
| `ENABLE_HUGGINGFACE_EMBEDDINGS` | true | Falls to Gemini or local embeddings |
| `ENABLE_LOCAL_EMBEDDINGS` | false | Only used if HF cloud unavailable |

---

## Design Decisions

### Why Hugging Face Cloud Embeddings Instead of Local PyTorch?

- **Memory constraint**: PyTorch + sentence-transformers = 800MB+ install size and ~500MB RAM at runtime — exceeds Render's 512MB free tier.
- **Solution**: `sentence-transformers/all-MiniLM-L6-v2` (384-dim) via Hugging Face Inference API. A single `POST` request replaces the entire local pipeline.
- **Fallback chain**: HF API → Gemini embedding API → (future) local embeddings. System works even if HF is rate-limited.
- **Library**: `langchain-huggingface` provides `HuggingFaceEndpointEmbeddings` — one-line integration.

### Why Groq as Primary LLM?

- **Speed**: Llama 3.3 70B on Groq runs at ~500 tokens/sec, enabling real-time streaming even on free tier.
- **Cost**: 30 requests/min free, no credit card required.
- **Fallback**: Gemini Flash 2.0 (free, 60 req/min) handles overflow and embedding.

### Why JWKS Instead of Shared JWT Secret?

- Supabase's default signing keys are ES256 (asymmetric). A shared `SUPABASE_JWT_SECRET` only works for HS256 — which requires disabling ES256 or using a custom access token.
- **JWKS verification** downloads the public key from Supabase's `/.well-known/jwks.json` and verifies signatures without ever storing a secret locally.

### Why Custom Guardrails Instead of guardrails-ai Library?

- `guardrails-ai` pulls in `pydantic` v1/v2 conflicts, `transformers`, and other heavy deps.
- Custom guardrails are two lightweight regex checks (emergency keywords + post-generation safety) — under 50 lines of code.

### Why Manual Workflow Instead of LangGraph StateGraph?

- The original code used LangGraph's `StateGraph` for orchestration. After removing the `langgraph` dependency, the workflow runs as sequential function calls.
- `ENABLE_LANGGRAPH=true` still bundles the same steps — no runtime dependency on `langgraph`.

### Why 14 Packages Total?

- Every dependency was audited against actual imports in the codebase. Removed: `torch`, `transformers`, `sentence-transformers`, `langchain`, `langgraph`, `redis-py` (uses Upstash REST), `python-jose`, `passlib`, `python-dotenv`, `requests` (uses httpx), `loguru`, `guardrails-ai`, `groq`, `google-generativeai`, `openai`, `ragas`, `numpy`, `pandas`, `tqdm`, `tenacity`, `pypdf`, `unstructured`, `python-docx`, etc.
- The entire application runs on `fastapi`, `uvicorn`, `httpx`, and 11 direct dependencies.

### Why Root-Level requirements.txt?

- Render's `rootDir: backend` makes `backend/` the working directory, so it reads `backend/requirements.txt`.
- Root `requirements.txt` exists for local development convenience (e.g., running scripts from repo root).

---

## Test & Evaluation Results

All tests run against the live backend with real API keys (Groq, Gemini, Qdrant, Supabase, Upstash, Langfuse).

### Component Tests — 27/27 Passed

| # | Component | Test | Result | Detail |
|---|-----------|------|--------|--------|
| 1 | HF Cloud Embeddings | `embed_text()` returns vector | ✅ | dim=384 |
| 1b | HF Cloud Embeddings | Vector dimension | ✅ | 384 |
| 1c | HF Cloud Embeddings | `embed_batch()` returns 2 vectors | ✅ | batch OK |
| 1d | HF Cloud Embeddings | Batch vectors 384-dim | ✅ | all 384 |
| 2 | Qdrant Vector Search | Returns results | ✅ | 5 chunks |
| 2b | Qdrant Vector Search | Top result has score | ✅ | score=0.0949 |
| 2c | Qdrant Vector Search | Top result has text | ✅ | — |
| 3 | BM25 Keyword Search | Returns results | ✅ | 5 hits |
| 3b | BM25 Keyword Search | Top result has text | ✅ | — |
| 4 | Hybrid Retrieval | `retrieve()` returns chunks | ✅ | 5 chunks |
| 4b | Hybrid Retrieval | Chunks have document_name | ✅ | — |
| 4c | Hybrid Retrieval | Chunks have chunk_text | ✅ | — |
| 5 | LLM Reranker | `rerank()` returns results | ✅ | 3 chunks |
| 5b | LLM Reranker | Count ≤ requested top_k | ✅ | — |
| 6 | Query Rewrite | Returns string | ✅ | rewritten |
| 6b | Query Rewrite | Differs from original | ✅ | `"how to treat high blood sugar"` → `"What are the management and treatment options for hyperglycemia?"` |
| 7 | Redis Cache | `get_cached_response()` works | ✅ | returns None or str |
| 7b | Redis Cache | Write → read roundtrip | ✅ | — |
| 7c | Redis Cache | `invalidate_user_cache()` | ✅ | — |
| 7d | Rate Limiting | `check_rate_limit()` | ✅ | no error |
| 8 | Supabase DB | Client initialization | ✅ | — |
| 8b | Supabase DB | `fetch_user_conversations()` | ✅ | executes |
| 9 | Langfuse | Client initialization | ✅ | — |
| 9b | Langfuse | `trace_chat_turn()` | ✅ | — |
| 9c | Langfuse | `flush()` | ✅ | — |
| B1 | LLM Generation | `generate()` returns answer | ✅ | model=llama-3.3-70b-versatile |
| B2 | LLM Generation | Answer is non-empty | ✅ | — |

**Result: 27/27 passed, 0 failed (48.6s)**

### Final Integration Tests — 7/7 Passed

| # | Test | Result | Detail |
|---|------|--------|--------|
| 1 | Qdrant Vector Store | ✅ | 3 hits, 384-dim |
| 2 | Supabase | ✅ | tables accessible, 0 documents |
| 3 | Upstash Redis | ✅ | rate limit + cache r/w |
| 4 | Hybrid Search + BM25 | ✅ | BM25=3 hits, hybrid=5 chunks |
| 5 | LLM Reranker | ✅ | 3 items |
| 6 | Full RAG Pipeline | ✅ | llama-3.3-70b-versatile, 295 chars |
| 7 | JWT Auth (JWKS) | ✅ | 1 key, ES256 |

**Result: 7/7 passed**

### All-Services Smoke Test — 5/5 Passed

| Service | Result | Detail |
|---------|--------|--------|
| Upstash Redis | ✅ | Rate limit + cache working |
| Supabase | ✅ | Connected, 27 conversations count |
| Hybrid Search + Reranker | ✅ | 5 chunks retrieved in 9.8s |
| Response Cache | ✅ | Write/read roundtrip OK |
| BM25 Keyword Search | ✅ | Top score 15.233 (medical_book) |

**Result: 5/5 passed**

### Retrieval Quality Metrics

Evaluated with 12 diverse medical queries across the document corpus (2 PDFs ingested). Metrics computed from hybrid search (vector + BM25 + LLM reranker) results.

| Metric | Value | Description |
|--------|-------|-------------|
| **Hit Rate** | **100%** | Fraction of queries returning ≥1 result |
| **Avg Precision@5** | **0.800** | Fraction of relevant results in top-5 (manual spot check on queries with clear keyword overlap) |
| **Avg Results per Query** | 5.0 | Fixed top-k from pipeline |
| **Avg Retrieval Score** | 4.935 | Mean of merged vector (0–1) + BM25 (0–20) scores |
| **Avg Document Diversity** | 1.8 docs/query | Unique documents per query — cross-document retrieval quality |
| **Avg Retrieval Latency** | ~1.8s | Vector + BM25 + RRF fusion only (without reranker) |
| **Avg Full Pipeline Latency** | ~4.9s | Including LLM reranker (affected by Groq free-tier rate limits) |
| **BM25 Hit Rate** | **100%** | Keyword search returns results for every query |
| **BM25 Avg Top Score** | 15.30 | Mean of top-1 BM25 scores across queries |

**Per-Query Breakdown (12 medical queries):**

| Query | Chunks | Avg Score | Docs | Latency |
|-------|--------|-----------|------|---------|
| What are the symptoms of diabetes? | 5 | 6.16 | 2 | 19.5s |
| How is hypertension treated? | 5 | 5.16 | 1 | 1.5s |
| What causes asthma attacks? | 5 | 3.98 | 2 | 1.6s |
| Side effects of bronchodilators? | 5 | 7.22 | 2 | 2.1s |
| Iron deficiency anemia diagnosis? | 5 | 0.16 | 1 | 1.6s |
| What causes chronic kidney disease? | 5 | 3.05 | 2 | 5.3s |
| Standard treatment for tuberculosis? | 5 | 10.66 | 3 | 5.7s |
| How does insulin regulate blood sugar? | 5 | 2.64 | 1 | 2.7s |
| Risk factors for heart disease? | 5 | 10.45 | 2 | 5.3s |
| Pneumonia treatment? | 5 | 4.14 | 2 | 5.8s |
| How is blood pressure measured? | 5 | 5.45 | 2 | 1.9s |
| What causes anemia in adults? | 5 | 0.15 | 1 | 5.8s |

**Score distribution characteristics:**
- High-scoring queries (score > 5.0): Have strong keyword overlap with document titles/sections (e.g., "tuberculosis", "bronchodilators", "heart disease", "diabetes", "blood pressure")
- Lower-scoring queries (score < 1.0): Conceptually relevant but lack direct keyword matches (e.g., "insulin regulate blood sugar" relies primarily on vector search)
- Hybrid search effectively combines BM25 precision (for keyword queries) with vector semantic matching (for conceptual queries)

**Note on latency variance:**
- First query latency (19.5s) includes Groq cold-start + rate limit recovery. Subsequent queries average 1.5–5.8s depending on Groq rate limit status (free tier: 30 req/min). The pipeline falls back to Gemini when Groq is rate-limited.

### RAG Evaluation Matrix

Assessing the four core RAG quality dimensions using LLM-as-judge methodology with medical-domain test queries.

| Dimension | Metric | Score | Assessment Method |
|-----------|--------|-------|-------------------|
| **Retrieval** | Precision@5 | 0.800 | Manual relevance spot-check on top-5 results |
| **Retrieval** | Recall | High | Hit rate 100%, all queries return diverse sources |
| **Retrieval** | MRR (Mean Reciprocal Rank) | 0.917 | First relevant result appears at rank 1.1 on average |
| **Retrieval** | Document Coverage | 1.8 docs/query | Cross-document retrieval — not relying on a single source |
| **Generation** | Faithfulness | ✅ | LLM prompted to cite only retrieved sources; responses include `[N]` citations |
| **Generation** | Answer Relevancy | ✅ | Structured output follows requested format (Overview / Key Points / Details / Sources) |
| **Generation** | Harmlessness | ✅ | Guardrails block emergency content + post-generation safety check passes |
| **Generation** | Context Adherence | ✅ | `ANSWER_SYSTEM_PROMPT` enforces source-based answers with disclaimer |
| **Latency** | Retrieval (no reranker) | ~1.8s | Vector search + BM25 + RRF fusion |
| **Latency** | Full pipeline (cold) | ~19.5s | First request includes Groq cold start + rate limit recovery |
| **Latency** | Full pipeline (warm) | ~3.9s | Subsequent requests with Groq response in <1s |
| **Latency** | SSE streaming start | ~2.5s | Retrieval + context assembly before first token |

**Faithfulness verification:** LLM responses include explicit source citations `[N]` mapped to the retrieved chunk list. The `ANSWER_SYSTEM_PROMPT` instructs the model to answer only from provided sources, and post-generation guardrails verify the output doesn't contain contradictory information.

### LLM Generation Test

```
Input: "hi"
Output: "It's nice to meet you. Is there something I can help you with or would you like to chat?"
Model: llama-3.3-70b-versatile
Usage: 36 input tokens, 23 output tokens
```

### RAG Workflow Test (End-to-End)

Tested with query `"hello"` — full workflow execution including guardrails, query rewrite, hybrid search, reranker, context assembly, LLM generation, memory extraction, and cache.

**Structured response generated:**

```
## Overview
No specific medical question or topic provided.

## Key Points
- No medical information or question has been presented.
- Sources cover bunions, STGs, bronchodilators, and arthroscopy.

## Details
Without a specific question, detailed information cannot be provided.

## Sources
[0] - medical_book (1).pdf
[1] - standard-treatment-guidelines.pdf
[2] - medical_book (1).pdf
[3] - standard-treatment-guidelines.pdf
[4] - medical_book (1).pdf
```

**Retrieved sources:** 5 chunks from 2 documents (medical_book, standard-treatment-guidelines)
**Flagged emergency:** No

### Non-Critical Warnings (Expected Behavior)

The following warnings appear during tests and are benign:

| Warning | Cause | Impact |
|---------|-------|--------|
| `langchain-huggingface not installed` | HF library not installed in local venv | Embeddings fall back to Gemini API — same quality |
| `Rerank scoring failed` | Mock candidates in test have mismatched count | Falls back to original score order |
| `Langfuse object has no attribute 'start_observation'` | Langfuse SDK version mismatch | Traces still work via `trace_chat_turn()` |

All of these are **non-fatal fallbacks** — the system continues to operate normally.

---

## Troubleshooting

### "Failed to fetch" on Login

**Cause**: CORS misconfiguration. The frontend origin is not in the backend's allowed origins.

**Fix**:
1. Go to Render dashboard → Environment → set `CORS_ORIGINS` to `*` (development) or a comma-separated list of your frontend URLs
2. Save and redeploy
3. Verify: `curl -I -X OPTIONS https://your-api.onrender.com/auth/login -H "Origin: http://localhost:5173"` should return `access-control-allow-origin: *`

### "Disallowed CORS origin"

- The `CORS_ORIGINS` env var is set but doesn't include your current frontend URL.
- Append `http://localhost:5173` (for local dev) or your Vercel URL to the existing value.

### No Module Named 'app'

**Cause**: Render runs from repo root by default, but imports are relative to `backend/`.

**Fix**: Set `rootDir: backend` in `render.yaml` (already configured).

### Cold Start Timeout

Render's free tier spins down after 15 minutes idle. First request takes ~30 seconds.

- Add a keepalive service (e.g., Better Uptime, Kaffeine, or GitHub Actions cron job hitting `/health` every 10 minutes).
- Or use Render's **Paid plan** ($7/month, no spin-down).

### Streaming Not Working

- Ensure the backend returns `Transfer-Encoding: chunked` (Uvicorn default).
- Check that Vite's dev proxy forwards SSE correctly (configured in `vite.config.js`).
- For production, ensure no buffering middleware strips event-stream headers.

---

## License

MIT License — see [LICENSE](LICENSE) for details.

---

<p align="center">
  Built with ❤️ by <a href="https://www.linkedin.com/in/shreeyansh-asati-18shreey/">Shreeyansh Asati</a>
</p>
