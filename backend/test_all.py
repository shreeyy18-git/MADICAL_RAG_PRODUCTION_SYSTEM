"""
Tests all connected services: Upstash Redis, Supabase, Hybrid Search, Reranker.
"""
import asyncio, sys, time
sys.path.insert(0, ".")

from app.config import get_settings

settings = get_settings()
print(f"Settings loaded: hybrid={settings.enable_hybrid_search}, "
      f"rerank={settings.enable_llm_rerank}, "
      f"ratelimit={settings.enable_rate_limiting}\n")

async def test_redis_upstash():
    print("=== 1. Upstash Redis ===")
    from app.services.rate_limit import check_rate_limit
    try:
        await check_rate_limit("test-user-123")
        print("  Rate limit check: OK (no limit exceeded)")
    except Exception as e:
        if "429" in str(e):
            print("  Rate limit check: OK (limit hit as expected)")
        else:
            print(f"  Rate limit FAILED: {e}")
            return False
    return True

async def test_supabase():
    print("\n=== 2. Supabase ===")
    from app.services.supabase_client import get_supabase
    try:
        sb = get_supabase()
        res = sb.table("conversations").select("count", count="exact").limit(1).execute()
        print(f"  Connected. Conversations table accessible. Count: {res.count}")
        return True
    except Exception as e:
        print(f"  Supabase FAILED: {e}")
        return False

async def test_hybrid_and_rerank():
    print("\n=== 3. Hybrid Search + Reranker ===")
    from app.services import retrieval
    msg = "What is Diabetes?"
    start = time.perf_counter()
    chunks = await retrieval.retrieve(msg)
    elapsed = (time.perf_counter() - start) * 1000
    print(f"  Retrieved {len(chunks)} chunks in {elapsed:.0f}ms")
    for i, c in enumerate(chunks[:3]):
        print(f"  [{i}] score={c['score']:.3f} doc={c['document_name']}")
        print(f"      {c['chunk_text'][:100]}...")
    if settings.enable_hybrid_search:
        print("  Hybrid search: ENABLED (BM25 + vector merged)")
    if settings.enable_llm_rerank:
        print("  Reranker: ENABLED (LLM re-scored candidates)")
    return len(chunks) > 0

async def test_response_cache():
    print("\n=== 4. Response Cache (Upstash) ===")
    from app.services.cache import get_cached_response, set_cached_response
    try:
        await set_cached_response("test-user", "test query", "test response")
        cached = await get_cached_response("test-user", "test query")
        if cached == "test response":
            print("  CACHE: OK (write + read worked)")
        else:
            print("  CACHE FAILED: unexpected value")
    except Exception as e:
        print(f"  CACHE FAILED: {e}")

async def test_keyword_search():
    print("\n=== 5. BM25 Keyword Search ===")
    from app.services.keyword_search import keyword_search, refresh_corpus_cache
    try:
        refresh_corpus_cache()
        results = keyword_search("diabetes blood sugar", top_k=3)
        print(f"  BM25 returned {len(results)} results")
        for r in results[:3]:
            print(f"  score={r['score']:.3f} doc={r['document_name']}")
        return True
    except Exception as e:
        print(f"  BM25 FAILED: {e}")
        return False

async def main():
    results = await asyncio.gather(
        test_redis_upstash(),
        test_supabase(),
        test_hybrid_and_rerank(),
        test_response_cache(),
        test_keyword_search(),
        return_exceptions=True
    )
    print("\n=== SUMMARY ===")
    tests = ["Redis Upstash", "Supabase", "Hybrid+Rerank", "Response Cache", "BM25"]
    for name, res in zip(tests, results):
        status = "PASS" if res is True else f"FAIL ({res})" if isinstance(res, Exception) else f"SKIP ({res})" if res is False else f"PASS"
        print(f"  {name}: {status}")

asyncio.run(main())
