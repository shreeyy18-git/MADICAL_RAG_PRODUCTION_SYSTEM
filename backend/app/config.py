"""
Centralized configuration.

Every external service is free-tier by design (see README for the
phase-by-phase free-tier mapping). Feature flags below let the same
codebase run as Phase 1, 2, or 3 without code changes -- just env vars.
"""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    environment: str = "development"

    # --- Supabase (auth, chat history, file storage) ---
    supabase_url: str = ""
    supabase_service_key: str = ""  # service_role key, used server-side only
    supabase_jwt_secret: str = ""   # used to verify user-issued JWTs

    # --- Qdrant Cloud (vector store) ---
    qdrant_url: str = ""
    qdrant_api_key: str = ""
    qdrant_collection: str = "medical_chunks"

    # --- Groq (primary LLM, fast + free) ---
    groq_api_key: str = ""
    groq_model: str = "llama-3.3-70b-versatile"

    # --- Gemini (fallback LLM + embeddings, free tier) ---
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"
    gemini_embedding_model: str = "gemini-embedding-001"

    # --- Hugging Face (cloud embeddings via Inference API, free tier) ---
    huggingfacehub_api_token: str = ""
    huggingface_embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"

    # all-MiniLM-L6-v2 produces 384-dim vectors.
    # If you switch back to Gemini embeddings, set this to 768 and re-ingest.
    embedding_dim: int = 384

    # --- Upstash Redis (rate limiting / cache, REST-based) ---
    upstash_redis_rest_url: str = ""
    upstash_redis_rest_token: str = ""
    rate_limit_per_minute: int = 10

    # --- Langfuse (observability, Phase 3) ---
    langfuse_public_key: str = ""
    langfuse_secret_key: str = ""
    langfuse_host: str = "https://cloud.langfuse.com"
    langfuse_base_url: str = ""  # alias so LANGFUSE_BASE_URL in .env works

    # --- Phase feature flags ---
    # Phase 1: vector-only retrieval, direct generation, auth + history
    # Phase 2: + hybrid (BM25+vector) retrieval, LLM rerank, query rewrite, memory, rate limiting
    # Phase 3: + guardrails, observability tracing
    # Phase A (enhancements): + response cache, LangGraph, local embeddings, LiteLLM, Qdrant memory
    enable_hybrid_search: bool = False
    enable_query_rewrite: bool = False
    enable_llm_rerank: bool = False
    enable_long_term_memory: bool = False
    enable_rate_limiting: bool = False
    enable_guardrails: bool = False
    enable_observability: bool = False

    # --- Response caching (Upstash Redis) ---
    enable_response_cache: bool = False
    response_cache_ttl_seconds: int = 86400

    # --- LangGraph workflow orchestration ---
    enable_langgraph: bool = False

    # --- Local embeddings (BAAI/bge-small-en-v1.5 via sentence-transformers) ---
    enable_local_embeddings: bool = False

    # --- Hugging Face cloud embeddings (sentence-transformers/all-MiniLM-L6-v2 via Inference API) ---
    # Recommended for free tier — no PyTorch, runs entirely in the cloud.
    # Set ENABLE_HUGGINGFACE_EMBEDDINGS=true and HUGGINGFACEHUB_API_TOKEN in .env.
    enable_huggingface_embeddings: bool = False

    # --- LiteLLM unified gateway ---
    llm_model: str = "groq/llama-3.3-70b-versatile"
    llm_fallback_model: str = "gemini/gemini-2.5-flash"

    # --- Qdrant memory collection ---
    enable_qdrant_memory: bool = False
    qdrant_memory_collection: str = "medical_memory"

    # --- Retrieval tuning ---
    retrieval_top_k: int = 20      # candidates pulled before rerank
    final_context_k: int = 5       # chunks actually sent to the LLM
    chunk_size_tokens: int = 400
    chunk_overlap_tokens: int = 60

    # --- Cross-session history ---
    enable_cross_session_history: bool = False
    session_similarity_threshold: float = 0.3

    # --- Admin ---
    admin_user_ids: str = ""       # comma-separated Supabase user IDs allowed to upload documents


@lru_cache
def get_settings() -> Settings:
    return Settings()
