from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000)
    conversation_id: str | None = None  # null -> start a new conversation


class SourceChunk(BaseModel):
    document_name: str
    chunk_text: str
    score: float


class ChatResponse(BaseModel):
    conversation_id: str
    answer: str
    sources: list[SourceChunk] = []
    flagged_emergency: bool = False


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str
    created_at: datetime


class DocumentUploadResponse(BaseModel):
    document_id: str
    filename: str
    chunks_indexed: int


class HealthResponse(BaseModel):
    status: str
    phase_flags: dict[str, bool]
