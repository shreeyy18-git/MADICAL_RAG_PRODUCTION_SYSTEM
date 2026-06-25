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

# CORS: allow Vercel frontend in production, any origin in dev.
# Override via CORS_ORIGINS env var (comma-separated).
# Example: CORS_ORIGINS="https://your-app.vercel.app"
import os
_cors_origins = os.getenv("CORS_ORIGINS", "*")
_origins = [o.strip() for o in _cors_origins.split(",") if o.strip()] if _cors_origins != "*" else ["*"]
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
