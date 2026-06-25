"""
Langfuse v4 Observability Service.

Uses the Langfuse v4 SDK (OpenTelemetry-based). The v4 SDK replaced `.trace()`,
`.span()` and `.generation()` with `start_observation()` / `start_as_current_observation()`.

Key differences from v2/v3:
  - No `lf.trace()` — use `lf.start_observation(name=..., as_type="span")` as the root span
  - User ID is set via `otel_span.set_attribute("user.id", user_id)` on the root span
  - Child spans: `root.start_observation(name=..., as_type="generation")`
  - Must call `.end()` on every span explicitly
  - Must call `lf.flush()` to guarantee spans reach Langfuse before the process sleeps

Gate: enable_observability (bool) in config.py
"""
import logging
from functools import lru_cache
from typing import Optional

from langfuse import Langfuse

from app.config import get_settings

logger = logging.getLogger(__name__)

# OTel span attributes used by Langfuse v4.
# Confirmed from: langfuse._client.attributes.LangfuseOtelSpanAttributes
_LANGFUSE_USER_ID_ATTR    = "user.id"
_LANGFUSE_SESSION_ID_ATTR = "session.id"


@lru_cache
def get_langfuse() -> Optional[Langfuse]:
    settings = get_settings()
    host = (settings.langfuse_base_url or settings.langfuse_host or "").strip()
    public_key = settings.langfuse_public_key.strip()
    secret_key = settings.langfuse_secret_key.strip()

    if not settings.enable_observability or not public_key:
        return None

    lf = Langfuse(
        public_key=public_key,
        secret_key=secret_key,
        host=host or "https://cloud.langfuse.com",
    )
    logger.info("Langfuse v4 observability initialized (host=%s)", host or "cloud.langfuse.com")
    return lf


def flush() -> None:
    """Flush all pending Langfuse spans — call on application shutdown."""
    lf = get_langfuse()
    if lf is not None:
        try:
            lf.flush()
        except Exception as exc:
            logger.warning("Langfuse flush on shutdown failed: %s", exc)



def trace_chat_turn(
    user_id: str,
    user_message: str,
    answer: str,
    retrieved_chunks: list[dict],
    model_used: str,
    latency_ms: float,
    error: Optional[str] = None,
    conversation_id: Optional[str] = None,
    usage: Optional[dict] = None,
) -> None:
    """
    Emit a full chat-turn trace to Langfuse using the v4 SDK.

    Parameters
    ----------
    conversation_id : mapped to Langfuse session_id so all turns of one
                      conversation are grouped in the dashboard.
    usage           : dict with keys 'input_tokens' / 'output_tokens' from the
                      LLM call; falls back to word-count estimation when absent.

    Trace tree:
      chat_turn  (root span)
        └─ retrieval   (span)
        └─ generation  (generation)
    """
    lf = get_langfuse()
    if lf is None:
        return

    try:
        metadata: dict = {"latency_ms": round(latency_ms, 2)}
        if error:
            metadata["error"] = error

        # ── Root span (becomes the Langfuse trace) ──────────────────────────
        root = lf.start_observation(
            name="chat_turn",
            input=user_message,
            output=answer,
            metadata=metadata,
        )

        # Tag user and session on the underlying OTel span
        root._otel_span.set_attribute(_LANGFUSE_USER_ID_ATTR, user_id)
        if conversation_id:
            root._otel_span.set_attribute(_LANGFUSE_SESSION_ID_ATTR, conversation_id)

        # ── Retrieval child span ─────────────────────────────────────────────
        top_score = retrieved_chunks[0].get("score", 0.0) if retrieved_chunks else 0.0
        retrieval = root.start_observation(
            name="retrieval",
            as_type="span",
            input=user_message,
            output={
                "chunk_count": len(retrieved_chunks),
                "top_score": round(float(top_score), 4),
            },
        )
        retrieval.end()

        # ── Generation child span ────────────────────────────────────────────
        # Prefer real token counts from the LLM response; fall back to word estimation.
        if usage and (usage.get("input_tokens") or usage.get("output_tokens")):
            token_details = {
                "input": int(usage.get("input_tokens", 0)),
                "output": int(usage.get("output_tokens", 0)),
            }
        elif answer:
            token_details = {
                "input": len(user_message.split()),
                "output": len(answer.split()),
            }
        else:
            token_details = None

        gen_kwargs: dict = {
            "name": "generation",
            "as_type": "generation",
            "model": model_used or "unknown",
            "input": user_message,
            "output": answer,
            "metadata": {"latency_ms": round(latency_ms, 2)},
        }
        if token_details:
            gen_kwargs["usage_details"] = token_details

        generation = root.start_observation(**gen_kwargs)
        generation.end()

        # ── Close root and flush ─────────────────────────────────────────────
        root.end()
        lf.flush()

    except Exception as exc:
        # Observability must never crash the main request path
        logger.warning("Langfuse trace failed (non-critical): %s", exc)
