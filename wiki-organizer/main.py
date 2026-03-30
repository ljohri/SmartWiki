"""FastAPI document organizer service."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import Annotated

import anthropic
import asyncpg
from fastapi import FastAPI, File, Form, Header, HTTPException, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from db import create_pool, log_submission
from organizer import process_single_file
from wikijs_api import WikiJsGraphQL

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("wiki-organizer")

pool: asyncpg.Pool | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global pool
    pool = await create_pool()
    yield
    if pool:
        await pool.close()
        pool = None


app = FastAPI(title="SmartWiki Organizer", version="1.0.0", lifespan=lifespan)

_origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins if _origins else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _verify_bearer(authorization: str | None) -> None:
    if not settings.organizer_api_key:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="ORGANIZER_API_KEY is not configured",
        )
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token")
    token = authorization.split(" ", 1)[1].strip()
    if token != settings.organizer_api_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")


@app.get("/api/health")
async def health():
    return {"status": "ok", "service": "wiki-organizer"}


@app.post("/api/submit")
async def submit_documents(
    title: Annotated[str, Form()],
    category: Annotated[str, Form()],
    tags: Annotated[str, Form()] = "",
    description: Annotated[str, Form()] = "",
    username: Annotated[str, Form()] = "unknown",
    files: Annotated[list[UploadFile], File()],
    authorization: Annotated[str | None, Header()] = None,
):
    _verify_bearer(authorization)

    if not settings.wikijs_api_token:
        raise HTTPException(status_code=500, detail="WIKIJS_API_TOKEN not configured")
    if not settings.anthropic_api_key:
        raise HTTPException(status_code=500, detail="ANTHROPIC_API_KEY not configured")

    if pool is None:
        raise HTTPException(status_code=500, detail="Database not ready")

    anthropic_client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    wiki = WikiJsGraphQL()
    results: list[dict] = []

    try:
        for uf in files:
            raw = await uf.read()
            if not raw:
                results.append(
                    {"success": False, "filename": uf.filename or "unknown", "error": "Empty file"}
                )
                continue

            out = await process_single_file(
                wiki=wiki,
                anthropic_client=anthropic_client,
                filename=uf.filename or "upload.bin",
                raw_bytes=raw,
                title=title,
                category=category,
                tags=tags,
                description=description,
                username=username,
            )
            results.append(out)

            ai_decision = out.get("ai_decision")
            await log_submission(
                pool,
                username=username,
                title=title,
                category=category,
                tags=[t.strip() for t in tags.split(",") if t.strip()],
                original_filename=uf.filename or "unknown",
                target_path=out.get("pagePath"),
                ai_decision=ai_decision if isinstance(ai_decision, dict) else None,
                status="success" if out.get("success") else "failed",
                error_message=out.get("error"),
            )
    finally:
        await wiki.aclose()

    return {"results": results}
