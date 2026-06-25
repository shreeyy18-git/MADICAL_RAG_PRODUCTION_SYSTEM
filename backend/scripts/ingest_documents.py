"""
Bulk-ingest PDFs straight into Qdrant, bypassing the HTTP API and
Supabase Storage -- useful for seeding your knowledge base from a local
folder of medical PDFs before you've wired up the frontend.

Usage:
    python scripts/ingest_documents.py /path/to/pdf/folder
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services import embeddings, vector_store  # noqa: E402
from app.services.chunking import chunk_text, extract_text  # noqa: E402


async def ingest_file(path: Path) -> None:
    print(f"Ingesting {path.name} ...")
    pdf_bytes = path.read_bytes()
    text = extract_text(pdf_bytes)
    chunks = chunk_text(text)
    if not chunks:
        print(f"  no extractable text in {path.name}, skipping")
        return

async def ingest_file(path: Path) -> None:
    print(f"Ingesting {path.name} ...")
    pdf_bytes = path.read_bytes()
    text = extract_text(pdf_bytes)
    chunks = chunk_text(text)
    if not chunks:
        print(f"  no extractable text in {path.name}, skipping")
        return

    # Batch embed all chunks at once (supports both local and Gemini).
    print(f"  embedding {len(chunks)} chunks ...")
    all_vectors = await embeddings.embed_batch(chunks, task_type="RETRIEVAL_DOCUMENT")
    print(f"  embedded all chunks, now upserting to Qdrant ...")

    count = vector_store.upsert_chunks(
        document_id=path.name,
        document_name=path.name,
        chunk_texts=chunks,
        chunk_vectors=all_vectors,
    )
    print(f"  indexed {count} chunks")


async def main(folder: str) -> None:
    pdf_dir = Path(folder)
    pdf_files = sorted(pdf_dir.glob("*.pdf"))
    if not pdf_files:
        print(f"No PDFs found in {pdf_dir}")
        return
    for pdf_path in pdf_files:
        await ingest_file(pdf_path)
    print(f"Done. Ingested {len(pdf_files)} documents.")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python scripts/ingest_documents.py /path/to/pdf/folder")
        sys.exit(1)
    asyncio.run(main(sys.argv[1]))
