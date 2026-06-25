from fastapi import APIRouter

from app.config import get_settings
from app.models.schemas import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    settings = get_settings()
    return HealthResponse(
        status="ok",
        phase_flags={
            "hybrid_search": settings.enable_hybrid_search,
            "query_rewrite": settings.enable_query_rewrite,
            "llm_rerank": settings.enable_llm_rerank,
            "long_term_memory": settings.enable_long_term_memory,
            "rate_limiting": settings.enable_rate_limiting,
            "guardrails": settings.enable_guardrails,
            "observability": settings.enable_observability,
            "huggingface_embeddings": settings.enable_huggingface_embeddings,
            "local_embeddings": settings.enable_local_embeddings,
        },
    )
