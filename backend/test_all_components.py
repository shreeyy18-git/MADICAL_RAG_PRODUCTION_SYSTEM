"""
Comprehensive component test — runs against the backend venv.
Tests every subsystem individually without touching the running server.
"""
import asyncio
import sys
import os
import time
import traceback

# Ensure we can import from app/
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.chdir(os.path.dirname(os.path.abspath(__file__)))

PASS = "[PASS]"
FAIL = "[FAIL]"
INFO = "[*]"

results = []


def report(name, ok, detail=""):
    status = PASS if ok else FAIL
    line = f"  {status}  {name}"
    if detail:
        line += f"  —  {detail}"
    print(line)
    results.append((name, ok))


async def test_hf_embeddings():
    """1. Hugging Face cloud embeddings (all-MiniLM-L6-v2, 384-dim)"""
    print(f"\n{INFO} [1/9] Hugging Face Cloud Embeddings")
    try:
        from app.services.embeddings import embed_text, embed_batch
        from app.config import get_settings

        s = get_settings()
        print(f"     Flag: enable_huggingface_embeddings={s.enable_huggingface_embeddings}")
        print(f"     Model: {s.huggingface_embedding_model}")
        print(f"     Token set: {'yes' if s.huggingfacehub_api_token else 'NO'}")

        vec = await embed_text("What is diabetes?", task_type="RETRIEVAL_QUERY")
        dim = len(vec)
        report("embed_text() returns vector", dim > 0, f"dim={dim}")
        report("Vector dimension is 384", dim == 384, f"got {dim}")

        # Batch test
        batch = await embed_batch(["hello world", "medical guideline"], task_type="RETRIEVAL_DOCUMENT")
        report("embed_batch() returns 2 vectors", len(batch) == 2, f"got {len(batch)}")
        report("Batch vectors are 384-dim", all(len(v) == 384 for v in batch))
    except Exception as e:
        report("HF embeddings", False, str(e))
        traceback.print_exc()


async def test_qdrant_vector_search():
    """2. Qdrant vector search"""
    print(f"\n{INFO} [2/9] Qdrant Vector Search")
    try:
        from app.services.embeddings import embed_text
        from app.services.vector_store import vector_search, ensure_collection

        ensure_collection()
        print("     Collection ensured OK")

        qvec = await embed_text("diabetes treatment", task_type="RETRIEVAL_QUERY")
        results_list = vector_search(qvec, top_k=5)
        report("vector_search() returns results", len(results_list) > 0, f"{len(results_list)} chunks")
        if results_list:
            top = results_list[0]
            report("Top result has score", "score" in top, f"score={top.get('score', 'N/A'):.4f}")
            report("Top result has text", len(top.get("chunk_text", "")) > 0)
    except Exception as e:
        report("Qdrant vector search", False, str(e))
        traceback.print_exc()


async def test_bm25_keyword_search():
    """3. BM25 keyword search"""
    print(f"\n{INFO} [3/9] BM25 Keyword Search")
    try:
        from app.services.keyword_search import keyword_search

        results_list = keyword_search("diabetes insulin", top_k=5)
        report("keyword_search() returns results", len(results_list) > 0, f"{len(results_list)} hits")
        if results_list:
            report("Top BM25 result has text", len(results_list[0].get("chunk_text", "")) > 0)
    except Exception as e:
        report("BM25 keyword search", False, str(e))
        traceback.print_exc()


async def test_hybrid_retrieval():
    """4. Hybrid search (vector + BM25 + RRF fusion)"""
    print(f"\n{INFO} [4/9] Hybrid Retrieval (Vector + BM25 + RRF)")
    try:
        from app.services.retrieval import retrieve

        chunks = await retrieve("What is the treatment for diabetes?")
        report("retrieve() returns chunks", len(chunks) > 0, f"{len(chunks)} chunks")
        if chunks:
            report("Chunks have document_name", "document_name" in chunks[0])
            report("Chunks have chunk_text", "chunk_text" in chunks[0])
    except Exception as e:
        report("Hybrid retrieval", False, str(e))
        traceback.print_exc()


async def test_reranker():
    """5. LLM Reranker"""
    print(f"\n{INFO} [5/9] LLM Reranker")
    try:
        from app.services.reranker import rerank
        from app.services.retrieval import retrieve

        chunks = await retrieve("hypertension management")
        if not chunks:
            report("Reranker (no candidates to rerank)", False, "retrieval returned 0 chunks")
            return

        reranked = await rerank("hypertension management", chunks, top_k=3)
        report("rerank() returns results", len(reranked) > 0, f"{len(reranked)} chunks")
        report("Reranked count <= requested top_k", len(reranked) <= 3)
    except Exception as e:
        report("LLM reranker", False, str(e))
        traceback.print_exc()


async def test_query_rewrite():
    """6. Query rewriting"""
    print(f"\n{INFO} [6/9] Query Rewriting")
    try:
        from app.services.query_rewrite import rewrite_query

        original = "how to treat high blood sugar"
        rewritten = await rewrite_query(original)
        report("rewrite_query() returns string", isinstance(rewritten, str) and len(rewritten) > 0)
        report("Rewritten differs from original", rewritten != original, f"-> \"{rewritten[:80]}\"")
    except Exception as e:
        report("Query rewrite", False, str(e))
        traceback.print_exc()


async def test_redis_cache_rate_limit():
    """7. Redis (Upstash) — cache + rate limiting"""
    print(f"\n{INFO} [7/9] Upstash Redis (Cache + Rate Limiting)")
    try:
        from app.services.cache import get_cached_response, set_cached_response, invalidate_user_cache

        user_id = "test-user-component-check"
        query = "component test query"
        cached = await get_cached_response(user_id, query)
        report("get_cached_response() works (returns None or str)", cached is None or isinstance(cached, str))

        await set_cached_response(user_id, query, "test answer", conversation_id="test-conv")
        cached2 = await get_cached_response(user_id, query, conversation_id="test-conv")
        report("Cache write->read roundtrip", cached2 == "test answer")
        await invalidate_user_cache(user_id)
        report("invalidate_user_cache() runs without error", True)
    except Exception as e:
        report("Redis cache", False, str(e))
        traceback.print_exc()

    try:
        from app.services.rate_limit import check_rate_limit

        await check_rate_limit("test-user-component-check")
        report("check_rate_limit() runs without error", True)
    except Exception as e:
        report("Rate limiting", False, str(e))


async def test_supabase():
    """8. Supabase DB connection"""
    print(f"\n{INFO} [8/9] Supabase DB")
    try:
        from app.services.supabase_client import get_supabase, fetch_user_conversations

        sb = get_supabase()
        report("get_supabase() returns client", sb is not None)

        # Try a simple query — fetch conversations for a dummy user (should return empty list)
        convs = fetch_user_conversations("00000000-0000-0000-0000-000000000000")
        report("fetch_user_conversations() executes", isinstance(convs, list))
    except Exception as e:
        report("Supabase DB", False, str(e))
        traceback.print_exc()


async def test_langfuse():
    """9. Langfuse observability"""
    print(f"\n{INFO} [9/9] Langfuse Observability")
    try:
        from app.services.observability import get_langfuse, flush, trace_chat_turn

        lf = get_langfuse()
        report("get_langfuse() returns client (or None if disabled)", lf is not None or True)

        # Try a trace call — should not raise
        trace_chat_turn(
            user_id="test-user",
            conversation_id="test-session",
            user_message="test message",
            answer="test answer",
            model_used="test-model",
            latency_ms=42.0,
            retrieved_chunks=[],
            usage={},
        )
        report("trace_chat_turn() executes without error", True)
        flush()
        report("flush() executes without error", True)
    except Exception as e:
        report("Langfuse", False, str(e))
        traceback.print_exc()


async def test_llm_generation():
    """Bonus: LLM generation (Groq primary, Gemini fallback)"""
    print(f"\n{INFO} [BONUS] LLM Generation (Groq -> Gemini)")
    try:
        from app.services.llm import generate

        answer, model, usage = await generate(
            [
                {"role": "system", "content": "You are a medical assistant. Answer briefly."},
                {"role": "user", "content": "What is diabetes in one sentence?"},
            ],
            temperature=0.3,
            max_tokens=100,
        )
        report("generate() returns answer", len(answer) > 0, f"model={model}")
        report("Answer is non-empty", len(answer) > 10)
    except Exception as e:
        report("LLM generation", False, str(e))
        traceback.print_exc()


async def main():
    print("=" * 70)
    print("  MEDICAL RAG — COMPREHENSIVE COMPONENT TEST")
    print("=" * 70)

    t0 = time.time()

    await test_hf_embeddings()
    await test_qdrant_vector_search()
    await test_bm25_keyword_search()
    await test_hybrid_retrieval()
    await test_reranker()
    await test_query_rewrite()
    await test_redis_cache_rate_limit()
    await test_supabase()
    await test_langfuse()
    await test_llm_generation()

    elapsed = time.time() - t0
    passed = sum(1 for _, ok in results if ok)
    failed = sum(1 for _, ok in results if not ok)
    total = len(results)

    print("\n" + "=" * 70)
    print(f"  RESULTS: {passed}/{total} passed, {failed} failed  ({elapsed:.1f}s)")
    print("=" * 70)
    if failed:
        print("\n  Failed tests:")
        for name, ok in results:
            if not ok:
                print(f"    {FAIL}  {name}")
    print()
    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    asyncio.run(main())
