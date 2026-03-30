"""Chunking, embeddings (Voyage AI), and Qdrant retrieval."""

from __future__ import annotations

import logging
import re
from typing import Any

import voyageai
from qdrant_client import QdrantClient
from qdrant_client.http import models as qm

from config import settings

logger = logging.getLogger("chatbot.rag")

WORD_CHUNK = 400
WORD_OVERLAP = 50


def split_into_chunks(text: str, chunk_words: int = WORD_CHUNK, overlap: int = WORD_OVERLAP) -> list[str]:
    words = re.findall(r"\S+\s*", text)
    if not words:
        return []
    chunks: list[str] = []
    i = 0
    step = max(chunk_words - overlap, 1)
    while i < len(words):
        piece = "".join(words[i : i + chunk_words]).strip()
        if piece:
            chunks.append(piece)
        i += step
    return chunks


def embed_texts_voyage(texts: list[str], *, input_type: str) -> list[list[float]]:
    if not settings.voyageai_api_key:
        raise RuntimeError("VOYAGEAI_API_KEY is not set")
    client = voyageai.Client(api_key=settings.voyageai_api_key)
    # batch in groups of 128
    out: list[list[float]] = []
    batch_size = 128
    for start in range(0, len(texts), batch_size):
        batch = texts[start : start + batch_size]
        embed_kwargs: dict = {
            "texts": batch,
            "model": settings.voyage_embedding_model,
            "input_type": input_type,
        }
        # output_dimension supported on voyage-3/voyage-4 clients >= 0.3; optional on 0.2.x
        if settings.voyage_embedding_dimension:
            embed_kwargs["output_dimension"] = settings.voyage_embedding_dimension
        try:
            res = client.embed(**embed_kwargs)
        except TypeError:
            embed_kwargs.pop("output_dimension", None)
            res = client.embed(**embed_kwargs)
        vecs = getattr(res, "embeddings", None) or getattr(res, "data", None)
        if vecs is None:
            raise RuntimeError("Unexpected Voyage embed response shape")
        out.extend(vecs)
    return out


def ensure_collection(client: QdrantClient) -> None:
    name = settings.qdrant_collection
    exists = False
    try:
        cols = client.get_collections().collections
        exists = any(c.name == name for c in cols)
    except Exception as e:
        logger.warning("Could not list collections: %s", e)
    if not exists:
        client.create_collection(
            collection_name=name,
            vectors_config=qm.VectorParams(
                size=settings.voyage_embedding_dimension,
                distance=qm.Distance.COSINE,
            ),
        )


def retrieve_relevant_chunks(
    qdrant: QdrantClient,
    question: str,
    top_k: int = 5,
) -> list[dict[str, Any]]:
    ensure_collection(qdrant)
    [qvec] = embed_texts_voyage([question], input_type="query")
    hits = qdrant.search(
        collection_name=settings.qdrant_collection,
        query_vector=qvec,
        limit=top_k,
        with_payload=True,
    )
    results: list[dict[str, Any]] = []
    for h in hits:
        pl = h.payload or {}
        results.append(
            {
                "score": h.score,
                "page_id": pl.get("page_id"),
                "page_title": pl.get("page_title"),
                "page_path": pl.get("page_path"),
                "content": pl.get("content"),
                "chunk_index": pl.get("chunk_index"),
            }
        )
    return results


def format_context_for_prompt(chunks: list[dict[str, Any]]) -> str:
    lines: list[str] = []
    for i, c in enumerate(chunks, 1):
        lines.append(
            f"### Source {i}: {c.get('page_title')} ({c.get('page_path')})\n{c.get('content','')}\n"
        )
    return "\n".join(lines)
