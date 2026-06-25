"""
Qdrant Cloud free tier: 0.5 vCPU / 1GB RAM / 4GB disk, permanent free
but auto-suspends after 7 days with no traffic (see the GitHub Actions
keep-alive workflow in .github/workflows/keepalive.yml).

Extended with A5: Qdrant Memory Collection for semantic long-term memory.
"""
from functools import lru_cache
from uuid import uuid4

from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels

from app.config import get_settings


@lru_cache
def get_qdrant() -> QdrantClient:
    settings = get_settings()
    return QdrantClient(url=settings.qdrant_url, api_key=settings.qdrant_api_key)


def ensure_collection() -> None:
    settings = get_settings()
    client = get_qdrant()
    if not client.collection_exists(settings.qdrant_collection):
        client.create_collection(
            collection_name=settings.qdrant_collection,
            vectors_config=qmodels.VectorParams(
                size=settings.embedding_dim, distance=qmodels.Distance.COSINE
            ),
        )
    else:
        # Safety check: warn if the existing collection dimension doesn't match
        # the configured embedding_dim (happens when switching embedding providers).
        info = client.get_collection(settings.qdrant_collection)
        existing_dim = info.config.params.vectors.size
        if isinstance(existing_dim, int) and existing_dim != settings.embedding_dim:
            raise RuntimeError(
                f"Qdrant collection '{settings.qdrant_collection}' was created with "
                f"{existing_dim}-dim vectors, but EMBEDDING_DIM is now "
                f"{settings.embedding_dim}. Delete the collection and re-ingest "
                f"documents after switching embedding providers."
            )


def upsert_chunks(
    document_id: str,
    document_name: str,
    chunk_texts: list[str],
    chunk_vectors: list[list[float]],
) -> int:
    settings = get_settings()
    client = get_qdrant()
    ensure_collection()
    batch_size = 100
    total = 0
    for start in range(0, len(chunk_texts), batch_size):
        batch_texts = chunk_texts[start : start + batch_size]
        batch_vectors = chunk_vectors[start : start + batch_size]
        points = [
            qmodels.PointStruct(
                id=str(uuid4()),
                vector=vector,
                payload={
                    "document_id": document_id,
                    "document_name": document_name,
                    "chunk_text": text,
                    "chunk_index": start + i,
                },
            )
            for i, (text, vector) in enumerate(zip(batch_texts, batch_vectors))
        ]
        client.upsert(collection_name=settings.qdrant_collection, points=points)
        total += len(points)
    return total


def vector_search(query_vector: list[float], top_k: int) -> list[dict]:
    settings = get_settings()
    client = get_qdrant()
    results = client.query_points(
        collection_name=settings.qdrant_collection,
        query=query_vector,
        limit=top_k,
        with_payload=True,
    ).points
    return [
        {
            "id": str(r.id),
            "document_name": r.payload.get("document_name", "unknown"),
            "chunk_text": r.payload.get("chunk_text", ""),
            "score": r.score,
        }
        for r in results
    ]


# ---------------------------------------------------------------------------
# A5: Qdrant Memory Collection -- optional semantic memory store
# ---------------------------------------------------------------------------


def ensure_memory_collection() -> None:
    """Create the medical_memory collection if it does not exist."""
    settings = get_settings()
    if not settings.enable_qdrant_memory:
        return
    client = get_qdrant()
    if not client.collection_exists(settings.qdrant_memory_collection):
        client.create_collection(
            collection_name=settings.qdrant_memory_collection,
            vectors_config=qmodels.VectorParams(
                size=settings.embedding_dim, distance=qmodels.Distance.COSINE
            ),
        )


def upsert_memory_fact(user_id: str, fact_text: str, fact_vector: list[float]) -> None:
    """Store a single memory fact as a vector in the memory collection."""
    settings = get_settings()
    if not settings.enable_qdrant_memory:
        return
    client = get_qdrant()
    ensure_memory_collection()
    client.upsert(
        collection_name=settings.qdrant_memory_collection,
        points=[
            qmodels.PointStruct(
                id=str(uuid4()),
                vector=fact_vector,
                payload={"user_id": user_id, "fact_text": fact_text},
            )
        ],
    )


def search_memory(user_id: str, query_vector: list[float], top_k: int = 5) -> list[str]:
    """Search the memory collection, filtered by user_id, returning fact_texts."""
    settings = get_settings()
    if not settings.enable_qdrant_memory:
        return []
    client = get_qdrant()
    ensure_memory_collection()
    results = client.query_points(
        collection_name=settings.qdrant_memory_collection,
        query=query_vector,
        query_filter=qmodels.Filter(
            must=[qmodels.FieldCondition(key="user_id", match=qmodels.MatchValue(value=user_id))]
        ),
        limit=top_k,
        with_payload=True,
    ).points
    return [r.payload.get("fact_text", "") for r in results if r.payload]
