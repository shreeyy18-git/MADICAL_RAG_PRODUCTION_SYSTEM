"""
Phase 1: vector-only retrieval.
Phase 2: adds BM25 keyword search merged with vector results (hybrid),
         plus optional LLM reranking. Both gated by config flags so the
         same function works for either phase.
"""
from app.config import get_settings
from app.services import embeddings, keyword_search, reranker, vector_store


def _merge_dedup(vector_results: list[dict], keyword_results: list[dict]) -> list[dict]:
    """Reciprocal-rank-fusion-style merge, deduped by chunk text."""
    seen: dict[str, dict] = {}
    for rank, item in enumerate(vector_results):
        key = item["chunk_text"]
        seen[key] = {**item, "fused_score": 1.0 / (rank + 60)}
    for rank, item in enumerate(keyword_results):
        key = item["chunk_text"]
        bonus = 1.0 / (rank + 60)
        if key in seen:
            seen[key]["fused_score"] += bonus
        else:
            seen[key] = {**item, "fused_score": bonus}
    return sorted(seen.values(), key=lambda x: x["fused_score"], reverse=True)


async def retrieve(query: str) -> list[dict]:
    settings = get_settings()
    query_vector = await embeddings.embed_text(query, task_type="RETRIEVAL_QUERY")
    vector_hits = vector_store.vector_search(query_vector, top_k=settings.retrieval_top_k)

    if settings.enable_hybrid_search:
        keyword_hits = keyword_search.keyword_search(query, top_k=settings.retrieval_top_k)
        candidates = _merge_dedup(vector_hits, keyword_hits)
    else:
        candidates = vector_hits

    if settings.enable_llm_rerank:
        return await reranker.rerank(query, candidates, top_k=settings.final_context_k)

    return candidates[: settings.final_context_k]
