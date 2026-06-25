"""
Reranking via an LLM relevance-scoring prompt instead of a local
cross-encoder (e.g. MiniLM). A local cross-encoder needs PyTorch or
ONNX Runtime in memory at all times; on a 512MB Render free instance
that consistently leaves too little headroom for FastAPI itself once
you add Uvicorn workers and request buffers. Groq is fast and free, so
an extra scoring call per query is a better trade than carrying a
multi-hundred-MB ML runtime in production.

If you outgrow the free tier and move to a paid Render instance with
more RAM, swap this module for a local cross-encoder without touching
any other code -- retrieval.py only calls `rerank()`.
"""
import json
import logging

from app.services.llm import generate

logger = logging.getLogger(__name__)

RERANK_SYSTEM_PROMPT = (
    "You score how relevant each passage is to the query, from 0 (irrelevant) "
    "to 10 (directly answers it). Respond with ONLY a JSON array of numbers, "
    "one score per passage, in the same order. No explanation."
)


async def rerank(query: str, candidates: list[dict], top_k: int) -> list[dict]:
    """candidates: list of dicts with at least a 'chunk_text' key.
    Returns the top_k candidates re-ordered by LLM-assigned relevance."""
    if not candidates:
        return []

    numbered = "\n".join(f"[{i}] {c['chunk_text'][:600]}" for i, c in enumerate(candidates))
    messages = [
        {"role": "system", "content": RERANK_SYSTEM_PROMPT},
        {"role": "user", "content": f"Query: {query}\n\nPassages:\n{numbered}"},
    ]
    try:
        raw, _, _ = await generate(messages, temperature=0.0, max_tokens=300)
        scores = json.loads(raw.strip().strip("```json").strip("```"))
        if len(scores) != len(candidates):
            raise ValueError("score count mismatch")
    except (json.JSONDecodeError, ValueError) as exc:
        logger.warning("Rerank scoring failed (%s); falling back to original order", exc)
        return candidates[:top_k]

    scored = sorted(zip(candidates, scores), key=lambda pair: pair[1], reverse=True)
    return [c for c, _ in scored[:top_k]]
