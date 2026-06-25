import asyncio, sys
sys.path.insert(0, ".")
from app.services import retrieval, llm

async def test():
    msg = "What is Diabetes?"
    chunks = await retrieval.retrieve(msg)
    print(f"=== Retrieved {len(chunks)} chunks from Qdrant ===")
    for i, c in enumerate(chunks[:3]):
        print(f"\n--- Chunk {i} (score: {c['score']:.3f}) from [{c['document_name']}] ---")
        print(c['chunk_text'][:300])
    
    context = "\n\n".join(f"[{i}] {c['chunk_text']}" for i,c in enumerate(chunks[:5]))
    answer, model, _ = await llm.generate([
        {"role": "system", "content": "Answer using ONLY the provided sources."},
        {"role": "user", "content": f"Sources:\n{context}\n\nQuestion: {msg}"}
    ])
    print(f"\n=== Answer ({model}) ===")
    print(answer)

asyncio.run(test())
