import logging

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status

from app.api.deps import CurrentUser, get_admin_user
from app.models.schemas import DocumentUploadResponse
from app.services import embeddings, vector_store
from app.services.chunking import chunk_text, extract_text
from app.services.keyword_search import refresh_corpus_cache
from app.services.supabase_client import record_document, upload_source_document

logger = logging.getLogger(__name__)
router = APIRouter()

MAX_FILE_SIZE_MB = 20


@router.post("/admin/ingest", response_model=DocumentUploadResponse)
async def ingest_document(
    file: UploadFile, admin: CurrentUser = Depends(get_admin_user)
) -> DocumentUploadResponse:
    if file.content_type != "application/pdf":
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Only PDF files are accepted")

    file_bytes = await file.read()
    if len(file_bytes) > MAX_FILE_SIZE_MB * 1024 * 1024:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"File exceeds {MAX_FILE_SIZE_MB}MB limit")

    # 1. Archive the original PDF in Supabase Storage (shared path).
    storage_path = upload_source_document(file.filename, file_bytes)

    # 2. Extract + chunk text in memory.
    text = extract_text(file_bytes)
    chunks = chunk_text(text)
    if not chunks:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "No extractable text found in PDF")

    # 3. Embed every chunk via Gemini's free embedding API (batched).
    vectors = await embeddings.embed_batch(chunks, task_type="RETRIEVAL_DOCUMENT")

    # 4. Store vectors + chunk text in Qdrant (shared collection).
    indexed = vector_store.upsert_chunks(
        document_id=file.filename,
        document_name=file.filename,
        chunk_texts=chunks,
        chunk_vectors=vectors,
    )

    # 5. Record metadata in Supabase (global document, track who uploaded).
    document_id = record_document(file.filename, storage_path, indexed, uploaded_by=admin.user_id)

    # Refresh the in-memory BM25 corpus so hybrid search sees this doc.
    refresh_corpus_cache()

    logger.info("Ingested %s: %d chunks by admin %s", file.filename, indexed, admin.user_id)
    return DocumentUploadResponse(document_id=document_id, filename=file.filename, chunks_indexed=indexed)
