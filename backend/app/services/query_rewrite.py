from app.services.llm import generate

REWRITE_SYSTEM_PROMPT = (
    "You rewrite a user's medical question into a clear, specific search query "
    "for a document retrieval system. Expand vague terms into proper medical "
    "terminology. Return ONLY the rewritten query, nothing else. If the original "
    "query is already clear, return it unchanged."
)


async def rewrite_query(original_query: str, recent_messages: list[dict] | None = None) -> str:
    history_context = ""
    if recent_messages:
        history_context = "\nRecent conversation:\n" + "\n".join(
            f"{m['role']}: {m['content']}" for m in recent_messages[-4:]
        )
    messages = [
        {"role": "system", "content": REWRITE_SYSTEM_PROMPT},
        {"role": "user", "content": f"{history_context}\n\nQuery: {original_query}"},
    ]
    rewritten, _, _ = await generate(messages, temperature=0.0, max_tokens=120)
    return rewritten.strip().strip('"')
