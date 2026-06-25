"""
Thin wrapper around the Supabase Python client. Used for:
  - chat history (conversations, messages)
  - long-term memory facts (Phase 2)
  - document metadata (Phase 1)

Uses the service_role key because this runs server-side only; row-level
security in Postgres still scopes data correctly because we always pass
the authenticated user_id explicitly in every query.
"""
from functools import lru_cache

from supabase import Client, create_client

from app.config import get_settings


@lru_cache
def get_supabase() -> Client:
    settings = get_settings()
    if not settings.supabase_url or not settings.supabase_service_key:
        raise RuntimeError("SUPABASE_URL / SUPABASE_SERVICE_KEY not configured")
    return create_client(settings.supabase_url, settings.supabase_service_key)


def count_conversation_messages(conversation_id: str) -> int:
    sb = get_supabase()
    res = sb.table("messages").select("id", count="exact").eq("conversation_id", conversation_id).execute()
    return res.count or 0


def fetch_last_session_messages(user_id: str, exclude_id: str | None = None, msg_limit: int = 6) -> list[dict]:
    """Fetch the most recent completed session's last N messages for a user."""
    sb = get_supabase()
    query = sb.table("conversations").select("id").eq("user_id", user_id).order("created_at", desc=True).limit(1)
    if exclude_id:
        query = query.neq("id", exclude_id)
    res = query.execute()
    if not res.data:
        return []
    past_id = res.data[0]["id"]
    msgs = (
        sb.table("messages")
        .select("role, content, created_at")
        .eq("conversation_id", past_id)
        .order("created_at", desc=True)
        .limit(msg_limit)
        .execute()
    )
    return list(reversed(msgs.data))


def get_or_create_conversation(user_id: str, conversation_id: str | None) -> str:
    sb = get_supabase()
    if conversation_id:
        existing = (
            sb.table("conversations")
            .select("id")
            .eq("id", conversation_id)
            .eq("user_id", user_id)
            .execute()
        )
        if existing.data:
            return conversation_id
    created = sb.table("conversations").insert({"user_id": user_id}).execute()
    return created.data[0]["id"]


def fetch_user_conversations(user_id: str) -> list[dict]:
    sb = get_supabase()
    res = (
        sb.table("conversations")
        .select("id, created_at, messages(content)")
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .execute()
    )
    # The first user message usually serves as the title
    out = []
    for conv in res.data:
        title = "New Conversation"
        msgs = conv.get("messages", [])
        if msgs and len(msgs) > 0:
            title = msgs[0].get("content", title)[:50] + "..."
        out.append({
            "id": conv["id"],
            "created_at": conv["created_at"],
            "title": title,
            "message_count": len(msgs),
        })
    return out


def fetch_recent_messages(conversation_id: str, limit: int = 10) -> list[dict]:
    sb = get_supabase()
    res = (
        sb.table("messages")
        .select("role, content, created_at")
        .eq("conversation_id", conversation_id)
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
    return list(reversed(res.data))


def fetch_all_messages(conversation_id: str) -> list[dict]:
    sb = get_supabase()
    res = (
        sb.table("messages")
        .select("role, content, created_at")
        .eq("conversation_id", conversation_id)
        .order("created_at", desc=False)
        .execute()
    )
    return res.data


def save_message(conversation_id: str, role: str, content: str) -> None:
    sb = get_supabase()
    sb.table("messages").insert(
        {"conversation_id": conversation_id, "role": role, "content": content}
    ).execute()


def delete_conversation(conversation_id: str, user_id: str) -> None:
    sb = get_supabase()
    sb.table("conversations").delete().eq("id", conversation_id).eq("user_id", user_id).execute()


def upload_source_document(filename: str, file_bytes: bytes) -> str:
    """Stores the original PDF in Supabase Storage (free 1GB bucket) so
    it never touches Render's ephemeral local disk. Uses a shared path
    since documents are global (not per-user). Returns the storage path."""
    sb = get_supabase()
    path = f"shared/{filename}"
    sb.storage.from_("medical-documents").upload(
        path, file_bytes, {"content-type": "application/pdf", "upsert": "true"}
    )
    return path


def record_document(filename: str, storage_path: str, chunk_count: int, uploaded_by: str | None = None) -> str:
    sb = get_supabase()
    res = (
        sb.table("documents")
        .insert(
            {
                "filename": filename,
                "storage_path": storage_path,
                "chunk_count": chunk_count,
                "uploaded_by": uploaded_by,
            }
        )
        .execute()
    )
    return res.data[0]["id"]
