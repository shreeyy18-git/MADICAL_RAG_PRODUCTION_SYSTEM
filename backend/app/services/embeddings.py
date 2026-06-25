"""
Embedding generation. Three modes, configurable via flags:

1. **Hugging Face Cloud** (recommended for free tier) — uses
   langchain-huggingface's HuggingFaceEndpointEmbeddings to call the
   HF Inference API. No local PyTorch needed, runs entirely in the cloud.
   Model: sentence-transformers/all-MiniLM-L6-v2 (384-dim).
   Gate with `ENABLE_HUGGINGFACE_EMBEDDINGS=true` and set
   `HUGGINGFACEHUB_API_TOKEN` in .env.

2. **Local (BAAI/bge-small-en-v1.5)** — uses sentence-transformers for
   offline embedding. 384-dim vectors. Gate with `ENABLE_LOCAL_EMBEDDINGS=true`
   and use a **separate Qdrant collection** (different vector size).
   Requires PyTorch (heavy RAM — not recommended for Render free tier).

3. **Gemini API** (default fallback) — calls Gemini's embedding API over HTTP.
   This was chosen to avoid pulling in PyTorch, which alone can exceed
   Render's free 512MB RAM ceiling before app code even runs.
"""
import asyncio
import logging

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)

GEMINI_EMBED_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:embedContent"
GEMINI_BATCH_EMBED_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/{model}:batchEmbedContents"
)

# Lazy-loaded embedding clients
_hf_embeddings = None
_local_model = None


def _get_hf_embeddings():
    """Lazy-load the HuggingFaceEndpointEmbeddings client (cloud Inference API)."""
    global _hf_embeddings
    if _hf_embeddings is None:
        try:
            from langchain_huggingface import HuggingFaceEndpointEmbeddings

            settings = get_settings()
            _hf_embeddings = HuggingFaceEndpointEmbeddings(
                model=settings.huggingface_embedding_model,
                huggingfacehub_api_token=settings.huggingfacehub_api_token,
            )
            logger.info(
                "Hugging Face cloud embeddings initialized (model=%s)",
                settings.huggingface_embedding_model,
            )
        except ImportError:
            logger.error(
                "langchain-huggingface not installed. "
                "Install with: pip install langchain-huggingface"
            )
            return None
        except Exception as exc:
            logger.error("Failed to initialize Hugging Face embeddings: %s", exc)
            return None
    return _hf_embeddings


def _get_local_model():
    """Lazy-load the BAAI/bge-small-en-v1.5 sentence-transformers model."""
    global _local_model
    if _local_model is None:
        try:
            from sentence_transformers import SentenceTransformer

            _local_model = SentenceTransformer("BAAI/bge-small-en-v1.5")
            logger.info("Loaded local embedding model: BAAI/bge-small-en-v1.5")
        except ImportError:
            logger.warning("sentence-transformers not installed — falling back to Gemini API")
            return None
    return _local_model


_local_checked = False
_local_available_flag = False


def _local_available():
    global _local_checked, _local_available_flag
    if not _local_checked:
        _local_checked = True
        _local_available_flag = _get_local_model() is not None
    return _local_available_flag


async def embed_text(text: str, task_type: str = "RETRIEVAL_DOCUMENT") -> list[float]:
    """Embed a single string. task_type should be RETRIEVAL_DOCUMENT for
    chunks at ingestion time and RETRIEVAL_QUERY for user questions.

    Priority:
    1. Hugging Face cloud (if enable_huggingface_embeddings=True)
    2. Local model (if enable_local_embeddings=True)
    3. Gemini API (default fallback)
    """
    settings = get_settings()

    # 1. Hugging Face cloud embeddings
    if settings.enable_huggingface_embeddings:
        hf = _get_hf_embeddings()
        if hf is not None:
            # HuggingFaceEndpointEmbeddings is sync — run in thread
            return await asyncio.to_thread(hf.embed_query, text)
        logger.warning("HF embeddings unavailable, falling through to next provider")

    # 2. Local embeddings
    if settings.enable_local_embeddings and _local_available():
        model = _get_local_model()
        # BAAI/bge-small-en-v1.5 uses 'query' or 'passage' prefix for asymmetric search
        prefix = "query: " if task_type == "RETRIEVAL_QUERY" else "passage: "
        return model.encode(prefix + text).tolist()

    # 3. Fallback: Gemini API
    url = GEMINI_EMBED_URL.format(model=settings.gemini_embedding_model)
    payload = {
        "content": {"parts": [{"text": text}]},
        "taskType": task_type,
        "outputDimensionality": settings.embedding_dim,
    }
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            url, params={"key": settings.gemini_api_key}, json=payload
        )
        resp.raise_for_status()
        data = resp.json()
    return data["embedding"]["values"]


async def embed_batch(texts: list[str], task_type: str = "RETRIEVAL_DOCUMENT") -> list[list[float]]:
    """Embed many chunks in one request -- use this during ingestion to
    stay well inside API rate limits.

    Priority:
    1. Hugging Face cloud (if enable_huggingface_embeddings=True)
    2. Local model (if enable_local_embeddings=True)
    3. Gemini API (default fallback)
    """
    settings = get_settings()

    # 1. Hugging Face cloud embeddings
    if settings.enable_huggingface_embeddings:
        hf = _get_hf_embeddings()
        if hf is not None:
            return await asyncio.to_thread(hf.embed_documents, texts)
        logger.warning("HF embeddings unavailable, falling through to next provider")

    # 2. Local embeddings
    if settings.enable_local_embeddings and _local_available():
        model = _get_local_model()
        prefix = "query: " if task_type == "RETRIEVAL_QUERY" else "passage: "
        prefixed = [prefix + t for t in texts]
        return model.encode(prefixed).tolist()

    # 3. Fallback: Gemini batch API
    url = GEMINI_BATCH_EMBED_URL.format(model=settings.gemini_embedding_model)
    requests = [
        {
            "model": f"models/{settings.gemini_embedding_model}",
            "content": {"parts": [{"text": t}]},
            "taskType": task_type,
            "outputDimensionality": settings.embedding_dim,
        }
        for t in texts
    ]
    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(
            url, params={"key": settings.gemini_api_key}, json={"requests": requests}
        )
        resp.raise_for_status()
        data = resp.json()
    return [item["values"] for item in data["embeddings"]]
