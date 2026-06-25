from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import auth, chat, documents, health, profile
from app.core.logging import configure_logging
from app.services.observability import flush as flush_observability

configure_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    flush_observability()


app = FastAPI(title="Medical RAG API", version="0.1.0", lifespan=lifespan)

# CORS: allow Vercel frontend + common dev origins.
# Set CORS_ORIGINS env var (comma-separated) for production domains.
# Example: CORS_ORIGINS="https://your-app.vercel.app,https://your-custom-domain.com"
import os
_cors_origins = os.getenv("CORS_ORIGINS", "*")
if _cors_origins == "*":
    _origins = ["*"]
else:
    _origins = [o.strip() for o in _cors_origins.split(",") if o.strip()]
    # Always include local dev origins alongside production domains
    _dev_origins = ["http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:5173"]
    for dev in _dev_origins:
        if dev not in _origins:
            _origins.append(dev)
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, tags=["health"])
app.include_router(documents.router, tags=["documents"])
app.include_router(chat.router, tags=["chat"])
app.include_router(auth.router, tags=["auth"])
app.include_router(profile.router, tags=["profile"])
