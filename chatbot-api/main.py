"""FastAPI RAG chatbot with optional web search."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import Annotated, Any

import anthropic
from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from qdrant_client import QdrantClient
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from config import settings
from ingest import run_ingestion_once, schedule_ingestion_loop
from rag import format_context_for_prompt, retrieve_relevant_chunks

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("chatbot-api")

limiter = Limiter(key_func=get_remote_address)

CHAT_RATE = f"{settings.chat_rate_limit_per_minute}/minute"


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    question: str
    history: list[ChatMessage] = Field(default_factory=list)


def _verify_chat_key(authorization: str | None) -> None:
    if not settings.chatbot_api_key:
        raise HTTPException(status_code=500, detail="CHATBOT_API_KEY not configured")
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    token = authorization.split(" ", 1)[1].strip()
    if token != settings.chatbot_api_key:
        raise HTTPException(status_code=401, detail="Invalid API key")


def _build_sources(chunks: list[dict[str, Any]], wiki_base: str) -> list[dict[str, str]]:
    base = wiki_base.rstrip("/")
    seen: set[tuple[str, str]] = set()
    out: list[dict[str, str]] = []
    for c in chunks:
        path = (c.get("page_path") or "").strip() or "/"
        title = (c.get("page_title") or path).strip()
        key = (path, title)
        if key in seen:
            continue
        seen.add(key)
        url = f"{base}{path}" if path.startswith("/") else f"{base}/{path}"
        out.append({"title": title, "path": path, "url": url})
    return out


def _anthropic_messages_from_history(history: list[ChatMessage]) -> list[dict[str, Any]]:
    msgs: list[dict[str, Any]] = []
    for m in history[-20:]:
        role = m.role if m.role in ("user", "assistant") else "user"
        msgs.append({"role": role, "content": m.content})
    return msgs


def _call_claude(system: str, user_messages: list[dict[str, Any]]) -> str:
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    tools = [
        {
            "type": "web_search_20250305",
            "name": "web_search",
            "max_uses": 5,
        }
    ]
    try:
        resp = client.messages.create(
            model=settings.anthropic_model,
            max_tokens=4096,
            system=system,
            messages=user_messages,
            tools=tools,
        )
    except Exception as e:
        logger.warning("Claude with web_search failed (%s); retrying without tools", e)
        resp = client.messages.create(
            model=settings.anthropic_model,
            max_tokens=4096,
            system=system,
            messages=user_messages,
        )

    parts: list[str] = []
    for block in resp.content:
        if block.type == "text":
            parts.append(block.text)
    return "\n".join(parts).strip() or "I could not generate a response."


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        await run_ingestion_once()
        logger.info("Initial ingestion completed")
    except Exception:
        logger.exception("Initial ingestion failed (Wiki.js may still be starting)")
    schedule_ingestion_loop()
    yield


app = FastAPI(title="SmartWiki Chatbot", version="1.0.0", lifespan=lifespan)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

_origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins if _origins else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
async def health():
    return {"status": "ok", "service": "chatbot-api"}


@app.post("/api/ingest")
async def ingest_trigger(authorization: Annotated[str | None, Header()] = None):
    _verify_chat_key(authorization)
    result = await run_ingestion_once()
    return result


@app.post("/api/chat")
@limiter.limit(CHAT_RATE)
async def chat(
    request: Request,
    body: ChatRequest,
    authorization: Annotated[str | None, Header()] = None,
):
    _ = request  # required by slowapi
    _verify_chat_key(authorization)

    if not settings.anthropic_api_key:
        raise HTTPException(status_code=500, detail="ANTHROPIC_API_KEY not configured")

    q_kwargs: dict[str, Any] = {"url": settings.qdrant_url}
    if settings.qdrant_api_key:
        q_kwargs["api_key"] = settings.qdrant_api_key
    qdrant = QdrantClient(**q_kwargs)

    chunks = retrieve_relevant_chunks(qdrant, body.question, top_k=5)
    context = format_context_for_prompt(chunks)
    system = f"""You are a helpful assistant for our internal company wiki.
Your job is to answer questions from team members accurately and concisely.

CONTEXT FROM WIKI (use this as your primary source):
{context}

RULES:
- Always prefer information from the wiki context above.
- Use web search only when the wiki context doesn't cover the question.
- Always cite your sources — for wiki pages include the page path, for web results include the URL.
- If you don't know the answer and can't find it, say so clearly.
- Keep answers concise but complete.
- Format responses in clean markdown.
"""

    prior = _anthropic_messages_from_history(body.history)
    prior.append({"role": "user", "content": body.question})
    answer = _call_claude(system=system, user_messages=prior)
    sources = _build_sources(chunks, settings.wiki_public_url)
    return {"answer": answer, "sources": sources}
