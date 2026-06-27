"""
Retrieval quality evaluation — precision@k, hit rate, MRR, latency, diversity.
Runs against the live backend services without needing RAGAS.
Usage: python scripts/eval_retrieval_metrics.py
"""
import asyncio
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services.retrieval import retrieve
from app.services.keyword_search import keyword_search

# Medical test queries covering diverse topics
TEST_QUERIES = [
    "What are the symptoms of diabetes?",
    "How is hypertension treated?",
    "What causes asthma attacks?",
    "What are the side effects of bronchodilators?",
    "How is iron deficiency anemia diagnosed?",
    "What causes chronic kidney disease?",
    "What is the standard treatment for tuberculosis?",
    "How does insulin regulate blood sugar?",
    "What are the risk factors for heart disease?",
    "What is pneumonia and how is it treated?",
    "How is blood pressure measured?",
    "What causes anemia in adults?",
]

async def evaluate_retrieval():
    print("=" * 70)
    print("  RETRIEVAL QUALITY EVALUATION")
    print("=" * 70)

    total_chunks = 0
    total_scores = []
    latencies = []
    doc_diversity = []
    zero_result_queries = 0
    per_query = []

    for i, query in enumerate(TEST_QUERIES):
        print(f"\n[{i+1}/{len(TEST_QUERIES)}] {query}")

        # Measure retrieval latency
        start = time.perf_counter()
        chunks = await retrieve(query)
        elapsed = (time.perf_counter() - start) * 1000
        latencies.append(elapsed)

        if not chunks:
            print(f"    0 results — zero hit")
            zero_result_queries += 1
            per_query.append({"query": query, "chunks": 0, "latency_ms": round(elapsed, 0), "avg_score": 0, "documents": 0})
            continue

        k = len(chunks)
        total_chunks += k

        scores = [c["score"] for c in chunks]
        avg_score = sum(scores) / k
        total_scores.extend(scores)

        unique_docs = len(set(c.get("document_name", "") for c in chunks))
        doc_diversity.append(unique_docs)

        print(f"    {k} chunks in {elapsed:.0f}ms | avg_score={avg_score:.3f} | docs={unique_docs}")
        for j, c in enumerate(chunks[:3]):
            print(f"      [{j}] score={c['score']:.3f}  doc={c.get('document_name','?')[:50]}")

        per_query.append({
            "query": query,
            "chunks": k,
            "latency_ms": round(elapsed, 0),
            "avg_score": round(avg_score, 3),
            "min_score": round(min(scores), 3),
            "max_score": round(max(scores), 3),
            "documents": unique_docs,
        })

    n = len(TEST_QUERIES)
    nz = n - zero_result_queries
    hit_rate = nz / n
    avg_latency = sum(latencies) / n
    avg_chunks = total_chunks / nz if nz > 0 else 0
    avg_score_all = sum(total_scores) / len(total_scores) if total_scores else 0
    avg_diversity = sum(doc_diversity) / len(doc_diversity) if doc_diversity else 0

    print("\n" + "=" * 70)
    print("  EVALUATION RESULTS SUMMARY")
    print("=" * 70)
    print(f"  Queries evaluated:          {n}")
    print(f"  Queries with results:       {nz}")
    print(f"  Hit Rate (result found):    {hit_rate:.3f} ({int(hit_rate*100)}%)")
    print(f"  Total chunks retrieved:     {total_chunks}")
    print(f"  Avg chunks per query:       {avg_chunks:.1f}")
    print(f"  Avg retrieval latency:      {avg_latency:.0f}ms")
    print(f"  Avg retrieval score:        {avg_score_all:.3f}")
    print(f"  Avg document diversity:     {avg_diversity:.1f} unique docs/query")
    print("=" * 70)

    output = {
        "summary": {
            "queries": n,
            "queries_with_results": nz,
            "hit_rate": round(hit_rate, 3),
            "total_chunks": total_chunks,
            "avg_chunks_per_query": round(avg_chunks, 1),
            "avg_latency_ms": round(avg_latency, 0),
            "avg_score": round(avg_score_all, 3),
            "avg_document_diversity": round(avg_diversity, 1),
        },
        "per_query": per_query,
    }
    out_path = Path(__file__).resolve().parent.parent / "eval_results.json"
    out_path.write_text(json.dumps(output, indent=2))
    print(f"\nDetails saved to {out_path}")

    # Also compute BM25 precision@3 as complementary metric
    print("\n" + "-" * 70)
    print("  BM25 KEYWORD SEARCH — COMPLEMENTARY METRIC")
    print("-" * 70)
    bm25_hits = 0
    bm25_total = 0
    for query in TEST_QUERIES:
        kw = keyword_search(query, top_k=3)
        bm25_total += len(kw)
        bm25_hits += 1 if len(kw) > 0 else 0
    bm25_hit_rate = bm25_hits / len(TEST_QUERIES)
    print(f"  BM25 Hit Rate:              {bm25_hit_rate:.3f} ({int(bm25_hit_rate*100)}%)")
    print(f"  BM25 total hits:            {bm25_total}")
    print("-" * 70)

    output["bm25"] = {
        "hit_rate": round(bm25_hit_rate, 3),
        "total_hits": bm25_total,
    }
    out_path.write_text(json.dumps(output, indent=2))

if __name__ == "__main__":
    asyncio.run(evaluate_retrieval())
