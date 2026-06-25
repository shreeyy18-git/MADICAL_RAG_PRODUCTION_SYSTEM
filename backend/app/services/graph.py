"""
A2: LangGraph Workflow Orchestration.

Replaces the linear sequential code in chat.py with a proper state-graph
workflow for better observability, state management, and conditional branching.

Each node calls existing service functions. Only activated when
`ENABLE_LANGGRAPH=true` in config.
"""
import logging
import time

from app.config import get_settings
from app.models.schemas import ChatResponse, SourceChunk
from app.services import guardrails, llm, memory, observability, query_rewrite, retrieval
from app.services.cache import get_cached_response, set_cached_response
from app.services.embeddings import embed_text
from app.services.supabase_client import (
    count_conversation_messages,
    fetch_last_session_messages,
    fetch_recent_messages,
    get_or_create_conversation,
    save_message,
)
from app.services.vector_store import search_memory, upsert_memory_fact

logger = logging.getLogger(__name__)

ANSWER_SYSTEM_PROMPT = (
    "You are a medical information assistant. Answer using ONLY the provided "
    "sources. Structure your response as follows:\n"
    "\n"
    "## Overview\n"
    "A concise 1-2 sentence summary of the answer.\n"
    "\n"
    "## Key Points\n"
    "- Bullet-point list of the most important findings, each cited with the "
    "source number in brackets, e.g. [1], [2].\n"
    "- Keep each bullet to one clear fact.\n"
    "\n"
    "## Details\n"
    "A deeper explanation if the question warrants it, with inline citations.\n"
    "\n"
    "## Sources\n"
    "List which source number corresponds to which document name.\n"
    "\n"
    "Rules:\n"
    "- If the sources don't contain the answer, say so plainly -- do not guess.\n"
    "- Always end with: *\"This information is for educational purposes only. "
    "Consult a qualified healthcare professional for medical advice.\"*\n"
    "- Cite which source number supports each claim using [N] notation."
)


# ---------------------------------------------------------------------------
# State definition
# ---------------------------------------------------------------------------

class RAGState:
    """Mutable state bag passed through the graph nodes."""
    def __init__(
        self,
        user_id: str,
        conversation_id: str | None,
        user_message: str,
    ):
        self.user_id = user_id
        self.conversation_id = conversation_id
        self.user_message = user_message
        self.search_query: str = ""
        self.retrieved_chunks: list[dict] = []
        self.reranked_chunks: list[dict] = []
        self.memory_facts: list[str] = []
        self.context_block: str = ""
        self.answer: str = ""
        self.model_used: str = ""
        self.is_cached: bool = False
        self.flagged_emergency: bool = False
        self.cached_response: str | None = None
        self.error: str | None = None
        self.start_time: float = time.perf_counter()

    def elapsed_ms(self) -> float:
        return (time.perf_counter() - self.start_time) * 1000


# ---------------------------------------------------------------------------
# Graph nodes (each is an async function that mutates state)
# ---------------------------------------------------------------------------

async def node_check_cache(state: RAGState) -> None:
    """Check if a cached response exists for this query."""
    if not get_settings().enable_response_cache:
        return
    cached = await get_cached_response(state.user_id, state.user_message, state.conversation_id or "")
    if cached:
        state.cached_response = cached
        state.is_cached = True
        logger.info("Cache HIT for user %s conv %s", state.user_id, state.conversation_id)


async def node_rate_limit(state: RAGState) -> None:
    """Check rate limit."""
    if get_settings().enable_rate_limiting:
        from app.services.rate_limit import check_rate_limit
        await check_rate_limit(state.user_id)


async def node_guardrails_emergency(state: RAGState) -> None:
    """Check for emergency keywords before any LLM call."""
    if get_settings().enable_guardrails and guardrails.detect_emergency(state.user_message):
        state.flagged_emergency = True
        state.answer = guardrails.EMERGENCY_RESPONSE


async def node_query_rewrite(state: RAGState) -> None:
    """Rewrite query if enabled."""
    settings = get_settings()
    if settings.enable_query_rewrite:
        recent = fetch_recent_messages(state.conversation_id, limit=10) if state.conversation_id else []
        state.search_query = await query_rewrite.rewrite_query(state.user_message, recent)
    else:
        state.search_query = state.user_message


async def node_memory_retrieval(state: RAGState) -> None:
    """Fetch memory facts from Supabase and/or Qdrant memory collection."""
    settings = get_settings()
    state.memory_facts = []

    if settings.enable_long_term_memory:
        state.memory_facts = memory.fetch_memories(state.user_id)

    if settings.enable_qdrant_memory:
        # Also fetch from Qdrant semantic memory
        query_embedding = await embed_text(state.search_query, task_type="RETRIEVAL_QUERY")
        qdrant_memories = search_memory(state.user_id, query_embedding, top_k=5)
        state.memory_facts.extend(qdrant_memories)
        # Deduplicate
        state.memory_facts = list(dict.fromkeys(state.memory_facts))


async def node_retrieval(state: RAGState) -> None:
    """Run hybrid/vector retrieval."""
    state.retrieved_chunks = await retrieval.retrieve(state.search_query)


async def _compute_cosine_similarity(a: list[float], b: list[float]) -> float:
    """Compute cosine similarity between two vectors."""
    import math
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if not na or not nb:
        return 0.0
    return dot / (na * nb)


async def _get_session_context(state: RAGState) -> str:
    """
    Build the session context block:
    - If current session has messages: last 3 messages from current session
    - If new session: fetch past 1 session, check relevance via embedding similarity
    """
    settings = get_settings()
    if state.conversation_id and count_conversation_messages(state.conversation_id) > 0:
        # Existing session — last 3 messages
        recent = fetch_recent_messages(state.conversation_id, limit=3)
        if not recent:
            return ""
        return "\n".join(f"{m['role']}: {m['content']}" for m in recent)

    # New session — check past 1 session if cross-session is enabled
    if not settings.enable_cross_session_history:
        return ""
    past = fetch_last_session_messages(state.user_id, exclude_id=state.conversation_id, msg_limit=6)
    if not past:
        return ""

    past_text = "\n".join(f"{m['role']}: {m['content']}" for m in past)
    try:
        from app.services.embeddings import embed_text
        query_vec = await embed_text(state.user_message, task_type="RETRIEVAL_QUERY")
        past_vec = await embed_text(past_text, task_type="RETRIEVAL_DOCUMENT")
        sim = await _compute_cosine_similarity(query_vec, past_vec)
    except Exception as exc:
        logger.warning("Similarity check failed, skipping past session: %s", exc)
        return ""

    if sim < settings.session_similarity_threshold:
        logger.info("Past session skipped (sim=%.3f < %.2f)", sim, settings.session_similarity_threshold)
        return ""

    logger.info("Past session included (sim=%.3f)", sim)
    return f"Previous session:\n{past_text}"


async def node_context_assembly(state: RAGState) -> None:
    """Assemble the context block from retrieved chunks, memory, profile, and session context."""
    chunks = state.reranked_chunks if state.reranked_chunks else state.retrieved_chunks
    context_block = "\n\n".join(
        f"[{i}] (source: {c['document_name']}) {c['chunk_text']}" for i, c in enumerate(chunks)
    )
    memory_block = "\n".join(f"- {fact}" for fact in state.memory_facts) if state.memory_facts else "None"

    profile_block = "None"
    try:
        from app.services.supabase_client import get_supabase
        res = get_supabase().table("profiles").select("name,age,phone,older_disease").eq("user_id", state.user_id).limit(1).execute()
        if res.data:
            p = res.data[0]
            parts = []
            if p.get("name"): parts.append(f"Name: {p['name']}")
            if p.get("age"): parts.append(f"Age: {p['age']}")
            if p.get("older_disease"): parts.append(f"Known conditions: {p['older_disease']}")
            if parts: profile_block = "; ".join(parts)
    except Exception:
        pass

    session_context = await _get_session_context(state)
    session_block = f"Current conversation:\n{session_context}" if session_context else "Current conversation:\n(none)"

    state.context_block = (
        f"Known facts about this user:\n{memory_block}\n\n"
        f"User profile:\n{profile_block}\n\n"
        f"{session_block}\n\n"
        f"Sources:\n{context_block}\n\n"
        f"Question: {state.user_message}"
    )


async def node_llm_generation(state: RAGState) -> None:
    """Call the LLM with assembled context."""
    messages = [
        {"role": "system", "content": ANSWER_SYSTEM_PROMPT},
        {"role": "user", "content": state.context_block},
    ]
    state.answer, state.model_used, usage = await llm.generate(messages)


async def node_safety_check(state: RAGState) -> None:
    """Post-generation safety check."""
    if get_settings().enable_guardrails:
        is_safe, reason = await guardrails.safety_check(state.user_message, state.answer)
        if not is_safe:
            logger.warning("Guardrail blocked response for user %s: %s", state.user_id, reason)
            state.answer = (
                "I can't provide a confident answer to that based on the available "
                "sources. Please consult a qualified clinician."
            )


async def node_store_history(state: RAGState) -> None:
    """Save conversation to supabase."""
    if state.conversation_id:
        save_message(state.conversation_id, "user", state.user_message)
        save_message(state.conversation_id, "assistant", state.answer)


async def node_cache_response(state: RAGState) -> None:
    """Cache the generated response."""
    if get_settings().enable_response_cache and not state.is_cached:
        await set_cached_response(state.user_id, state.user_message, state.answer, state.conversation_id or "")


async def node_extract_memory(state: RAGState) -> None:
    """Extract and store memory facts."""
    settings = get_settings()
    if settings.enable_long_term_memory:
        await memory.extract_and_store(state.user_id, state.user_message, state.answer)

    if settings.enable_qdrant_memory:
        try:
            query_embedding = await embed_text(state.user_message)
            # Store the full exchange as a memory fact
            fact_text = f"User asked about: {state.user_message[:200]}"
            upsert_memory_fact(state.user_id, fact_text, query_embedding)
        except Exception as exc:
            logger.warning("Qdrant memory extraction failed: %s", exc)


async def node_trace(state: RAGState) -> None:
    """Send trace to Langfuse if enabled."""
    if get_settings().enable_observability:
        observability.trace_chat_turn(
            user_id=state.user_id,
            user_message=state.user_message,
            answer=state.answer,
            retrieved_chunks=state.retrieved_chunks,
            model_used=state.model_used,
            latency_ms=state.elapsed_ms(),
            conversation_id=state.conversation_id,
        )


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

async def run_rag_workflow(
    user_id: str,
    conversation_id: str | None,
    user_message: str,
) -> ChatResponse:
    """
    Execute the RAG pipeline as a sequential workflow.

    This is a simplified orchestrator that calls nodes in order.
    For production use, wrap with actual `StateGraph` from langgraph.
    """
    state = RAGState(
        user_id=user_id,
        conversation_id=conversation_id,
        user_message=user_message,
    )

    # Run nodes in order
    try:
        try:
            await node_check_cache(state)
        except Exception as e:
            state.answer = f"Failed at node_check_cache: [{type(e).__name__}] {e}"
            return _state_to_response(state)

        if state.cached_response:
            state.answer = state.cached_response
            state.model_used = "cache"
            await node_store_history(state)
            await node_trace(state)
            return _state_to_response(state)

        try:
            await node_rate_limit(state)
        except Exception as e:
            state.answer = f"Failed at node_rate_limit: [{type(e).__name__}] {e}"
            return _state_to_response(state)

        await node_guardrails_emergency(state)
        if state.flagged_emergency:
            await node_store_history(state)
            await node_trace(state)
            return _state_to_response(state)

        await node_query_rewrite(state)

        try:
            await node_memory_retrieval(state)
        except Exception as e:
            state.answer = f"Failed at node_memory_retrieval: [{type(e).__name__}] {e}"
            return _state_to_response(state)

        try:
            await node_retrieval(state)
        except Exception as e:
            state.answer = f"Failed at node_retrieval: [{type(e).__name__}] {e}"
            return _state_to_response(state)

        try:
            await node_context_assembly(state)
        except Exception as e:
            state.answer = f"Failed at node_context_assembly: [{type(e).__name__}] {e}"
            return _state_to_response(state)

        try:
            await node_llm_generation(state)
        except Exception as e:
            state.answer = f"Failed at node_llm_generation: [{type(e).__name__}] {e}"
            return _state_to_response(state)

        try:
            await node_safety_check(state)
        except Exception as e:
            state.answer = f"Failed at node_safety_check: [{type(e).__name__}] {e}"
            return _state_to_response(state)

        try:
            await node_store_history(state)
        except Exception as e:
            state.answer = f"Failed at node_store_history: [{type(e).__name__}] {e}"
            return _state_to_response(state)

        try:
            await node_cache_response(state)
        except Exception as e:
            state.answer = f"Failed at node_cache_response: [{type(e).__name__}] {e}"
            return _state_to_response(state)

        try:
            await node_extract_memory(state)
        except Exception as e:
            state.answer = f"Failed at node_extract_memory: [{type(e).__name__}] {e}"
            return _state_to_response(state)

        try:
            await node_trace(state)
        except Exception as e:
            state.answer = f"Failed at node_trace: [{type(e).__name__}] {e}"
            return _state_to_response(state)

    except Exception as exc:
        logger.exception("RAG workflow failed for user %s", user_id)
        state.error = str(exc)
        state.answer = f"Internal error [{type(exc).__name__}]: {exc}"

    return _state_to_response(state)


async def run_rag_workflow_stream(
    user_id: str,
    conversation_id: str | None,
    user_message: str,
):
    """
    Streaming RAG workflow. Yields dict events:
      - {"type": "token", "content": "..."} — streamed LLM tokens
      - {"type": "metadata", "conversation_id": "...", "sources": [...], "model": "..."}
      - {"type": "error", "content": "..."}
    """
    state = RAGState(
        user_id=user_id,
        conversation_id=conversation_id,
        user_message=user_message,
    )

    try:
        try:
            await node_check_cache(state)
        except Exception as e:
            yield {"type": "error", "content": f"Cache check failed: {e}"}
            return

        if state.cached_response:
            state.answer = state.cached_response
            state.model_used = "cache"
            await node_store_history(state)
            await node_trace(state)
            yield {"type": "token", "content": state.answer}
            yield _metadata_event(state)
            return

        try:
            await node_rate_limit(state)
        except Exception as e:
            yield {"type": "error", "content": f"Rate limited: {e}"}
            return

        await node_guardrails_emergency(state)
        if state.flagged_emergency:
            await node_store_history(state)
            await node_trace(state)
            yield {"type": "token", "content": state.answer}
            yield _metadata_event(state)
            return

        await node_query_rewrite(state)

        try:
            await node_memory_retrieval(state)
        except Exception as e:
            yield {"type": "error", "content": f"Memory retrieval failed: {e}"}
            return

        try:
            await node_retrieval(state)
        except Exception as e:
            yield {"type": "error", "content": f"Retrieval failed: {e}"}
            return

        try:
            await node_context_assembly(state)
        except Exception as e:
            yield {"type": "error", "content": f"Context assembly failed: {e}"}
            return

        # --- Streaming LLM generation ---
        messages = [
            {"role": "system", "content": ANSWER_SYSTEM_PROMPT},
            {"role": "user", "content": state.context_block},
        ]

        full_answer = ""
        model_used = ""
        usage = {}
        try:
            async for evt in llm.generate_stream(messages):
                if evt["type"] == "token":
                    full_answer += evt["content"]
                    yield evt
                elif evt["type"] == "done":
                    model_used = evt.get("model", "")
                    usage = evt.get("usage", {})
        except Exception as e:
            yield {"type": "error", "content": f"Generation failed: {e}"}
            return

        state.answer = full_answer
        state.model_used = model_used

        # Post-generation nodes
        try:
            await node_safety_check(state)
        except Exception as e:
            yield {"type": "error", "content": f"Safety check failed: {e}"}
            return

        try:
            await node_store_history(state)
        except Exception as e:
            logger.warning("History store failed: %s", e)

        try:
            await node_cache_response(state)
        except Exception as e:
            logger.warning("Cache store failed: %s", e)

        try:
            await node_extract_memory(state)
        except Exception as e:
            logger.warning("Memory extract failed: %s", e)

        try:
            await node_trace(state)
        except Exception as e:
            logger.warning("Trace failed: %s", e)

    except Exception as exc:
        logger.exception("Streaming RAG workflow failed for user %s", user_id)
        yield {"type": "error", "content": str(exc)}
        return

    yield _metadata_event(state)


def _metadata_event(state: RAGState) -> dict:
    chunks = state.reranked_chunks if state.reranked_chunks else state.retrieved_chunks
    return {
        "type": "metadata",
        "conversation_id": state.conversation_id or "",
        "answer": state.answer,
        "model": state.model_used,
        "sources": [
            {
                "document_name": c.get("document_name", "unknown"),
                "chunk_text": c.get("chunk_text", "")[:300],
                "score": c.get("score", 0.0),
            }
            for c in chunks
        ],
        "flagged_emergency": state.flagged_emergency,
    }


def _state_to_response(state: RAGState) -> ChatResponse:
    """Convert the final state to a ChatResponse."""
    chunks = state.reranked_chunks if state.reranked_chunks else state.retrieved_chunks
    return ChatResponse(
        conversation_id=state.conversation_id or "",
        answer=state.answer,
        sources=[
            SourceChunk(
                document_name=c.get("document_name", "unknown"),
                chunk_text=c.get("chunk_text", "")[:300],
                score=c.get("score", 0.0),
            )
            for c in chunks
        ],
        flagged_emergency=state.flagged_emergency,
    )