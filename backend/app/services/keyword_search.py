"""
BM25 keyword search running in-process via rank-bm25 -- no external
service, no extra infra cost. Tradeoff: the corpus is rebuilt from
Qdrant on each cold start (cheap at hobby-project scale; revisit if the
document set grows past a few thousand chunks).
"""
from functools import lru_cache

from rank_bm25 import BM25Okapi

from app.services.vector_store import get_qdrant
from app.config import get_settings


def _tokenize(text: str) -> list[str]:
    return text.lower().split()


@lru_cache
def _load_corpus() -> tuple[BM25Okapi, list[dict]]:
    settings = get_settings()
    client = get_qdrant()
    points, _ = client.scroll(
        collection_name=settings.qdrant_collection,
        limit=10_000,
        with_payload=True,
        with_vectors=False,
    )
    corpus = [
        {
            "id": str(p.id),
            "document_name": p.payload.get("document_name", "unknown"),
            "chunk_text": p.payload.get("chunk_text", ""),
        }
        for p in points
    ]
    tokenized = [_tokenize(c["chunk_text"]) for c in corpus]
    bm25 = BM25Okapi(tokenized) if tokenized else None
    return bm25, corpus


def refresh_corpus_cache() -> None:
    """Call after ingesting new documents so BM25 picks them up."""
    _load_corpus.cache_clear()


def keyword_search(query: str, top_k: int) -> list[dict]:
    bm25, corpus = _load_corpus()
    if bm25 is None:
        return []
    scores = bm25.get_scores(_tokenize(query))
    ranked = sorted(zip(corpus, scores), key=lambda pair: pair[1], reverse=True)[:top_k]
    return [{**chunk, "score": float(score)} for chunk, score in ranked if score > 0]
