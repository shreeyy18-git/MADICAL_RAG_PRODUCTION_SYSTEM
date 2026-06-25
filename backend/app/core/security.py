"""
Verifies Supabase-issued JWTs server-side. Supports both:
1. Legacy symmetric JWT secret (HS256) — set SUPABASE_JWT_SECRET
2. New asymmetric JWKS (RS256/ES256) — uses SUPABASE_URL to fetch keys
"""
import httpx
import jwt
from fastapi import Depends, Header, HTTPException, status
from jwt import PyJWKClient

from app.config import get_settings


class CurrentUser:
    def __init__(self, user_id: str, email: str | None):
        self.user_id = user_id
        self.email = email


_jwks_client: PyJWKClient | None = None


def _get_jwks_client() -> PyJWKClient:
    global _jwks_client
    if _jwks_client is None:
        settings = get_settings()
        jwks_url = f"{settings.supabase_url}/auth/v1/.well-known/jwks.json"
        _jwks_client = PyJWKClient(jwks_url, cache_keys=True)
    return _jwks_client


def verify_supabase_jwt(token: str) -> CurrentUser:
    settings = get_settings()

    # Try JWKS first (new Supabase asymmetric keys)
    if settings.supabase_url:
        try:
            client = _get_jwks_client()
            signing_key = client.get_signing_key_from_jwt(token)
            payload = jwt.decode(
                token,
                signing_key.key,
                algorithms=["RS256", "ES256"],
                audience="authenticated",
                leeway=30,
                options={"verify_exp": True, "verify_iat": False},
            )
            user_id = payload.get("sub")
            if not user_id:
                raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Token missing subject")
            return CurrentUser(user_id=user_id, email=payload.get("email"))
        except Exception:
            pass  # Fall through to legacy method

    # Fallback: legacy symmetric JWT secret (HS256)
    if not settings.supabase_jwt_secret:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Server misconfigured: set SUPABASE_JWT_SECRET or SUPABASE_URL for JWKS",
        )
    try:
        payload = jwt.decode(
            token,
            settings.supabase_jwt_secret,
            algorithms=["HS256"],
            audience="authenticated",
        )
    except jwt.PyJWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid or expired token: {exc}",
        ) from exc

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token missing subject")
    return CurrentUser(user_id=user_id, email=payload.get("email"))


def get_current_user(authorization: str = Header(...)) -> CurrentUser:
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Bearer token",
        )
    token = authorization.removeprefix("Bearer ").strip()
    return verify_supabase_jwt(token)


def get_admin_user(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    """
    Verifies the authenticated user is in the admin list.
    Only users whose IDs are in ADMIN_USER_IDS can upload documents.
    """
    from app.config import get_settings

    settings = get_settings()
    admin_ids = [uid.strip() for uid in settings.admin_user_ids.split(",") if uid.strip()]
    if not admin_ids:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No admin users configured",
        )
    if user.user_id not in admin_ids:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admin users can perform this action",
        )
    return user
