import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.api.deps import CurrentUser, get_current_user
from app.services.supabase_client import get_supabase

logger = logging.getLogger(__name__)
router = APIRouter()


class ProfileResponse(BaseModel):
    name: str = ""
    age: int | None = None
    phone: str = ""
    older_disease: str = ""
    updated_at: str = ""


class ProfileUpdate(BaseModel):
    name: str = ""
    age: int | None = None
    phone: str = ""
    older_disease: str = ""


def _load(sb, user_id) -> dict | None:
    try:
        res = sb.table("profiles").select("*").eq("user_id", user_id).limit(1).execute()
        return res.data[0] if res.data else None
    except Exception as exc:
        logger.warning("Profile load failed: %s", exc)
        return None


def _save(sb, user_id, payload: dict) -> None:
    try:
        payload["updated_at"] = datetime.now(timezone.utc).isoformat()
        existing = sb.table("profiles").select("user_id").eq("user_id", user_id).limit(1).execute()
        if existing.data:
            sb.table("profiles").update(payload).eq("user_id", user_id).execute()
        else:
            payload["user_id"] = user_id
            sb.table("profiles").insert(payload).execute()
    except Exception as exc:
        logger.warning("Profile DB save failed: %s", exc)
        raise


@router.get("/api/profile", response_model=ProfileResponse)
async def get_profile(user: CurrentUser = Depends(get_current_user)):
    sb = get_supabase()
    p = _load(sb, user.user_id) or {}
    return ProfileResponse(
        name=p.get("name", ""),
        age=p.get("age"),
        phone=p.get("phone", ""),
        older_disease=p.get("older_disease", ""),
        updated_at=p.get("updated_at", ""),
    )


@router.put("/api/profile", response_model=ProfileResponse)
async def update_profile(body: ProfileUpdate, user: CurrentUser = Depends(get_current_user)):
    sb = get_supabase()
    payload = body.model_dump(exclude_none=True)
    _save(sb, user.user_id, payload)
    p = _load(sb, user.user_id) or {}
    return ProfileResponse(
        name=p.get("name", ""),
        age=p.get("age"),
        phone=p.get("phone", ""),
        older_disease=p.get("older_disease", ""),
        updated_at=p.get("updated_at", ""),
    )
