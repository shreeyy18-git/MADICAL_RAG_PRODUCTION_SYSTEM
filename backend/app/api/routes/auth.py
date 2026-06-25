import logging

import httpx
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from app.config import get_settings

logger = logging.getLogger(__name__)
router = APIRouter()


class AuthRequest(BaseModel):
    email: str
    password: str


class AuthResponse(BaseModel):
    user_id: str
    email: str
    access_token: str


@router.post("/auth/register", response_model=AuthResponse)
async def register(req: AuthRequest):
    """Register a new user via Supabase admin API (no email confirmation needed)."""
    settings = get_settings()
    headers = {
        "apikey": settings.supabase_service_key,
        "Authorization": f"Bearer {settings.supabase_service_key}",
        "Content-Type": "application/json",
    }
    async with httpx.AsyncClient(timeout=15) as client:
        # Create user via Admin API - bypasses email confirmation
        resp = await client.post(
            f"{settings.supabase_url}/auth/v1/admin/users",
            headers=headers,
            json={"email": req.email, "password": req.password, "email_confirm": True},
        )
        if resp.status_code == 429:
            raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "Rate limited. Try again later.")
        if not resp.is_success:
            detail = resp.json().get("msg", resp.text)
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail)

        user = resp.json()
        user_id = user.get("id")

        # Sign them in immediately to get a JWT token
        signin_resp = await client.post(
            f"{settings.supabase_url}/auth/v1/token?grant_type=password",
            headers={"apikey": settings.supabase_service_key, "Content-Type": "application/json"},
            json={"email": req.email, "password": req.password},
        )
        if not signin_resp.is_success:
            # User created but sign-in failed - that's ok, return user info
            return AuthResponse(user_id=user_id, email=req.email, access_token="")

        token_data = signin_resp.json()
        return AuthResponse(
            user_id=user_id,
            email=req.email,
            access_token=token_data.get("access_token", ""),
        )


@router.post("/auth/login", response_model=AuthResponse)
async def login(req: AuthRequest):
    """Sign in with email/password and return JWT."""
    settings = get_settings()
    headers = {
        "apikey": settings.supabase_service_key,
        "Content-Type": "application/json",
    }
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(
            f"{settings.supabase_url}/auth/v1/token?grant_type=password",
            headers=headers,
            json={"email": req.email, "password": req.password},
        )
        if not resp.is_success:
            detail = resp.json().get("error_description", resp.json().get("msg", resp.text))
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail)

        data = resp.json()
        return AuthResponse(
            user_id=data["user"]["id"],
            email=data["user"]["email"],
            access_token=data["access_token"],
        )
