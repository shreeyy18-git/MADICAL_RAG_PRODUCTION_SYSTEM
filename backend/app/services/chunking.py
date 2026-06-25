"""
Parses PDFs with PyMuPDF and splits into overlapping word-based chunks.
Runs entirely in memory -- never writes to local disk, because Render's
free tier has no persistent filesystem (anything written locally is
gone the moment the instance sleeps or restarts).
"""
import fitz  # PyMuPDF

from app.config import get_settings


def extract_text(pdf_bytes: bytes) -> str:
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    try:
        return "\n".join(page.get_text() for page in doc)
    finally:
        doc.close()


def chunk_text(text: str) -> list[str]:
    """Simple word-window chunker. Token-size fields in Settings are
    approximated as word counts (close enough for English medical text,
    avoids pulling in a tokenizer library)."""
    settings = get_settings()
    words = text.split()
    size = settings.chunk_size_tokens
    overlap = settings.chunk_overlap_tokens
    step = max(size - overlap, 1)

    chunks = []
    for start in range(0, len(words), step):
        chunk_words = words[start : start + size]
        if not chunk_words:
            break
        chunk = " ".join(chunk_words).strip()
        if chunk:
            chunks.append(chunk)
        if start + size >= len(words):
            break
    return chunks
