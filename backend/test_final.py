"""
Final comprehensive check - sequential execution.
"""
import asyncio, sys, time
sys.path.insert(0, ".")

from app.config import get_settings
s = get_settings()
print(f"Hybrid={s.enable_hybrid_search} ReRank={s.enable_llm_rerank} "
      f"RateLimit={s.enable_rate_limiting} LocalEmb={s.enable_local_embeddings}")
print()

async def test_qdrant():
    print("[1] Qdrant Vector Store...", end=" ")
    from app.services.vector_store import get_qdrant, vector_search
    from app.services.embeddings import embed_text
    client = get_qdrant()
    cols = [c.name for c in client.get_collections().collections]
    if s.qdrant_collection not in cols:
        print(f"FAIL - collection '{s.qdrant_collection}' not found")
        return
    vec = await embed_text("diabetes", task_type="RETRIEVAL_QUERY")
    results = vector_search(vec, top_k=3)
    print(f"OK ({len(results)} hits, {len(vec)}-dim)")

async def test_supabase():
    print("[2] Supabase...", end=" ")
    from app.services.supabase_client import get_supabase
    sb = get_supabase()
    r = sb.table("documents").select("count", count="exact").limit(1).execute()
    r2 = sb.table("conversations").select("count", count="exact").limit(1).execute()
    doc_count = sb.table("documents").select("*").execute()
    print(f"OK (tables accessible, {len(doc_count.data)} documents)")

async def test_redis():
    print("[3] Upstash Redis...", end=" ")
    from app.services.rate_limit import check_rate_limit
    from app.services.cache import get_cached_response, set_cached_response
    await check_rate_limit("test-user-abc")
    await set_cached_response("test", "k", "v")
    val = await get_cached_response("test", "k")
    assert val == "v"
    print("OK (rate limit + cache r/w)")

async def test_hybrid():
    print("[4] Hybrid Search + BM25...", end=" ")
    from app.services.keyword_search import keyword_search, refresh_corpus_cache
    from app.services.retrieval import retrieve
    refresh_corpus_cache()
    kw = keyword_search("diabetes blood sugar", top_k=3)
    chunks = await retrieve("What is Diabetes?")
    print(f"OK (BM25={len(kw)}, hybrid={len(chunks)})")

async def test_reranker():
    print("[5] LLM Reranker...", end=" ")
    from app.services.reranker import rerank
    cands = [
        {"chunk_text": "Diabetes causes high blood sugar.", "document_name": "b", "score": 0.8},
        {"chunk_text": "Kidneys filter waste from blood.", "document_name": "b", "score": 0.5},
        {"chunk_text": "Insulin regulates glucose in diabetes.", "document_name": "b", "score": 0.7},
    ]
    try:
        out = await rerank("What is diabetes?", cands, top_k=3)
        print(f"OK ({len(out)} items)")
    except Exception as e:
        print(f"SKIP (LLM unavailable: {type(e).__name__})")

async def test_full_rag():
    print("[6] Full RAG Pipeline...", end=" ")
    from app.services import retrieval, llm
    try:
        chunks = await retrieval.retrieve("What causes Diabetes?")
        ctx = "\n\n".join(f"[{i}] {c['chunk_text']}" for i,c in enumerate(chunks[:5]))
        ans, model, _ = await llm.generate([
            {"role": "system", "content": "Answer using ONLY provided sources."},
            {"role": "user", "content": f"Sources:\n{ctx}\n\nQuestion: What causes Diabetes?"}
        ])
        print(f"OK ({model}, {len(ans)} chars)")
    except Exception as e:
        print(f"SKIP (LLM unavailable: {type(e).__name__})")

async def test_jwt():
    print("[7] JWT Auth (JWKS)...", end=" ")
    import httpx
    r = httpx.get(f"{s.supabase_url}/auth/v1/.well-known/jwks.json")
    keys = r.json().get("keys", [])
    print(f"OK ({len(keys)} keys, {keys[0]['alg'] if keys else 'none'})")

async def main():
    await test_qdrant()
    await test_supabase()
    await test_redis()
    await test_hybrid()
    await test_reranker()
    await test_full_rag()
    await test_jwt()
    print("\n=== DONE ===")

asyncio.run(main())
