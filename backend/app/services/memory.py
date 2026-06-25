"""
Lightweight long-term memory: stored as plain text rows in Supabase
(not a separate vector index) to avoid a second Qdrant collection on
the free 1GB cluster. At hobby-project scale, a user has at most a few
dozen memory facts -- fetching all of them and letting the LLM use
what's relevant is simpler and cheaper than embedding-based memory
retrieval, and it avoids burning extra Qdrant disk quota.
"""
import json
import logging

from app.services.llm import generate
from app.services.supabase_client import get_supabase

logger = logging.getLogger(__name__)

EXTRACT_SYSTEM_PROMPT = (
    "Extract any durable medical facts about the user from this exchange that "
    "would be useful to remember in future conversations (allergies, chronic "
    "conditions, medications, past diagnoses). Respond with ONLY a JSON array "
    "of short fact strings. If there is nothing worth remembering, respond with []."
)


def fetch_memories(user_id: str) -> list[str]:
    sb = get_supabase()
    res = sb.table("memory_facts").select("fact_text").eq("user_id", user_id).execute()
    return [row["fact_text"] for row in res.data]


def _save_fact(user_id: str, fact_text: str) -> None:
    sb = get_supabase()
    sb.table("memory_facts").insert({"user_id": user_id, "fact_text": fact_text}).execute()


async def extract_and_store(user_id: str, user_message: str, assistant_message: str) -> None:
    messages = [
        {"role": "system", "content": EXTRACT_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": f"User: {user_message}\nAssistant: {assistant_message}",
        },
    ]
    try:
        raw, _, _ = await generate(messages, temperature=0.0, max_tokens=200)
        facts = json.loads(raw.strip().strip("```json").strip("```"))
    except (json.JSONDecodeError, ValueError) as exc:
        logger.warning("Memory extraction failed to parse (%s); skipping", exc)
        return

    for fact in facts:
        _save_fact(user_id, fact)
