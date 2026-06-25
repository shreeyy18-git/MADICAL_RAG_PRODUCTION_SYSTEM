import logging
import math
import time

import json

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app.api.deps import CurrentUser, get_current_user
from app.config import get_settings
from app.models.schemas import ChatRequest, ChatResponse, SourceChunk
from app.services import guardrails, llm, memory, observability, query_rewrite, rate_limit, retrieval
from app.services.supabase_client import (
    count_conversation_messages,
    delete_conversation,
    fetch_last_session_messages,
    fetch_recent_messages,
    get_or_create_conversation,
    save_message,
    fetch_user_conversations,
    fetch_all_messages,
)

logger = logging.getLogger(__name__)
router = APIRouter()


async def _cosine_similarity(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if not na or not nb:
        return 0.0
    return dot / (na * nb)


async def _build_session_context(user_id: str, conversation_id: str | None, user_message: str) -> str:
    """Build session context for the fallback (non-LangGraph) path."""
    settings = get_settings()
    if conversation_id and count_conversation_messages(conversation_id) > 0:
        recent = fetch_recent_messages(conversation_id, limit=3)
        if not recent:
            return ""
        return "\n".join(f"{m['role']}: {m['content']}" for m in recent)

    if not settings.enable_cross_session_history:
        return ""
    past = fetch_last_session_messages(user_id, exclude_id=conversation_id, msg_limit=6)
    if not past:
        return ""

    past_text = "\n".join(f"{m['role']}: {m['content']}" for m in past)
    try:
        from app.services.embeddings import embed_text
        query_vec = await embed_text(user_message, task_type="RETRIEVAL_QUERY")
        past_vec = await embed_text(past_text, task_type="RETRIEVAL_DOCUMENT")
        sim = await _cosine_similarity(query_vec, past_vec)
    except Exception as exc:
        logger.warning("Similarity check failed, skipping past session: %s", exc)
        return ""

    if sim < settings.session_similarity_threshold:
        logger.info("Past session skipped (sim=%.3f < %.2f)", sim, settings.session_similarity_threshold)
        return ""
    logger.info("Past session included (sim=%.3f)", sim)
    return f"Previous session:\n{past_text}"


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


@router.get("/chat/history")
async def get_history(user: CurrentUser = Depends(get_current_user)) -> list[dict]:
    return fetch_user_conversations(user.user_id)


@router.get("/chat/history/{conversation_id}")
async def get_conversation(conversation_id: str, user: CurrentUser = Depends(get_current_user)) -> list[dict]:
    return fetch_all_messages(conversation_id)


@router.delete("/chat/history/{conversation_id}")
async def delete_conversation_endpoint(conversation_id: str, user: CurrentUser = Depends(get_current_user)):
    delete_conversation(conversation_id, user.user_id)
    return {"ok": True}


@router.post("/chat/stream")
async def chat_stream(req: ChatRequest, user: CurrentUser = Depends(get_current_user)):
    """Streaming chat endpoint. Returns SSE events."""
    settings = get_settings()

    if settings.enable_rate_limiting:
        await rate_limit.check_rate_limit(user.user_id)

    if settings.enable_guardrails and guardrails.detect_emergency(req.message):
        conversation_id = get_or_create_conversation(user.user_id, req.conversation_id)
        save_message(conversation_id, "user", req.message)
        save_message(conversation_id, "assistant", guardrails.EMERGENCY_RESPONSE)
        async def emergency_stream():
            yield f"data: {json.dumps({'type': 'token', 'content': guardrails.EMERGENCY_RESPONSE})}\n\n"
            yield f"data: {json.dumps({'type': 'metadata', 'conversation_id': conversation_id, 'sources': [], 'flagged_emergency': True})}\n\n"
        return StreamingResponse(emergency_stream(), media_type="text/event-stream")

    conversation_id = get_or_create_conversation(user.user_id, req.conversation_id)

    async def event_stream():
        from app.services.graph import run_rag_workflow_stream
        async for evt in run_rag_workflow_stream(user.user_id, conversation_id, req.message):
            yield f"data: {json.dumps(evt)}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest, user: CurrentUser = Depends(get_current_user)) -> ChatResponse:
    settings = get_settings()
    start = time.perf_counter()

    # --- Phase 2: rate limiting ---
    if settings.enable_rate_limiting:
        await rate_limit.check_rate_limit(user.user_id)

    # --- Phase 3: emergency keyword check, before any LLM call ---
    if settings.enable_guardrails and guardrails.detect_emergency(req.message):
        conversation_id = get_or_create_conversation(user.user_id, req.conversation_id)
        save_message(conversation_id, "user", req.message)
        save_message(conversation_id, "assistant", guardrails.EMERGENCY_RESPONSE)
        return ChatResponse(
            conversation_id=conversation_id,
            answer=guardrails.EMERGENCY_RESPONSE,
            sources=[],
            flagged_emergency=True,
        )

    conversation_id = get_or_create_conversation(user.user_id, req.conversation_id)

    # --- Phase A: LangGraph workflow orchestration (caching, graph pipeline, Qdrant memory) ---
    if settings.enable_langgraph:
        from app.services.graph import run_rag_workflow  # lazy import avoids circular deps

        return await run_rag_workflow(
            user_id=user.user_id,
            conversation_id=conversation_id,
            user_message=req.message,
        )

    # --------------------------------------------------------------------------
    # Fallback: original sequential pipeline (when ENABLE_LANGGRAPH=false)
    # --------------------------------------------------------------------------
    save_message(conversation_id, "user", req.message)

    # --- Phase 2: query rewriting ---
    search_query = req.message
    if settings.enable_query_rewrite:
        recent_messages = fetch_recent_messages(conversation_id, limit=10)
        search_query = await query_rewrite.rewrite_query(req.message, recent_messages)

    # --- Phase 1/2: retrieval (vector-only, or hybrid + rerank if enabled) ---
    chunks = await retrieval.retrieve(search_query)

    # --- Phase 2: long-term memory ---
    memory_facts: list[str] = []
    if settings.enable_long_term_memory:
        memory_facts = memory.fetch_memories(user.user_id)

    # --- Session context (cross-session aware) ---
    session_ctx = await _build_session_context(user.user_id, conversation_id, req.message)
    session_block = f"Current conversation:\n{session_ctx}" if session_ctx else "Current conversation:\n(none)"

    context_block = "\n\n".join(
        f"[{i}] (source: {c['document_name']}) {c['chunk_text']}" for i, c in enumerate(chunks)
    )
    memory_block = "\n".join(f"- {fact}" for fact in memory_facts) if memory_facts else "None"

    messages = [
        {"role": "system", "content": ANSWER_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                f"Known facts about this user:\n{memory_block}\n\n"
                f"{session_block}\n\n"
                f"Sources:\n{context_block}\n\n"
                f"Question: {req.message}"
            ),
        },
    ]
    answer, model_used, usage = await llm.generate(messages)

    # --- Phase 3: post-generation safety check ---
    flagged_emergency = False
    if settings.enable_guardrails:
        is_safe, reason = await guardrails.safety_check(req.message, answer)
        if not is_safe:
            logger.warning("Guardrail blocked a response for user %s: %s", user.user_id, reason)
            answer = (
                "I can't provide a confident answer to that based on the available "
                "sources. Please consult a qualified clinician."
            )

    save_message(conversation_id, "assistant", answer)

    # --- Phase 2: async memory extraction (fire-and-forget would be better in
    # production; kept synchronous here for clarity) ---
    if settings.enable_long_term_memory:
        await memory.extract_and_store(user.user_id, req.message, answer)

    # --- Phase 3: observability ---
    if settings.enable_observability:
        observability.trace_chat_turn(
            user_id=user.user_id,
            user_message=req.message,
            answer=answer,
            retrieved_chunks=chunks,
            model_used=model_used,
            latency_ms=(time.perf_counter() - start) * 1000,
            conversation_id=conversation_id,
            usage=usage,
        )

    return ChatResponse(
        conversation_id=conversation_id,
        answer=answer,
        sources=[
            SourceChunk(document_name=c["document_name"], chunk_text=c["chunk_text"][:300], score=c.get("score", 0.0))
            for c in chunks
        ],
        flagged_emergency=flagged_emergency,
    )
