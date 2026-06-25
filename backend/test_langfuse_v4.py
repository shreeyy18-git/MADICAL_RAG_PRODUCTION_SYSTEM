"""Quick smoke test for the updated observability service."""
import sys
sys.path.insert(0, ".")

# Force env to look loaded for the test
import os
os.environ["LANGFUSE_PUBLIC_KEY"] = "pk-lf-be863ecc-dc0a-4d97-a1a7-1745e3c00b6e"
os.environ["LANGFUSE_SECRET_KEY"] = "sk-lf-1617f5e1-1763-4373-a834-0c1ede38299e"
os.environ["LANGFUSE_BASE_URL"] = "https://cloud.langfuse.com"
os.environ["ENABLE_OBSERVABILITY"] = "true"

from app.services.observability import trace_chat_turn, get_langfuse

lf = get_langfuse()
if lf is None:
    print("ERROR: Langfuse client is None — check env vars and enable_observability")
    sys.exit(1)

print(f"Langfuse client initialized: {type(lf).__name__}")

# Fire a test trace
trace_chat_turn(
    user_id="test-user-smoke",
    user_message="What is diabetes?",
    answer="Diabetes is a chronic condition affecting blood sugar levels.",
    retrieved_chunks=[{"score": 0.92, "document_name": "test.pdf", "chunk_text": "..."}],
    model_used="llama-3.3-70b-versatile",
    latency_ms=1234.5,
)

print("Trace emitted successfully — check your Langfuse dashboard!")
