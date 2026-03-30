"""Wiki.js -> chunk -> embed -> Qdrant."""

from __future__ import annotations

import asyncio
import logging
import uuid
from typing import Any

import httpx
from qdrant_client import QdrantClient
from qdrant_client.http import models as qm

from config import settings
from rag import embed_texts_voyage, ensure_collection, split_into_chunks
from wikijs_client import get_page_content, list_all_pages

logger = logging.getLogger("chatbot.ingest")


def _point_uuid(page_id: int, chunk_index: int) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"smartwiki:{page_id}:{chunk_index}"))


async def run_ingestion_once() -> dict[str, Any]:
    if not settings.wikijs_api_token:
        raise RuntimeError("WIKIJS_API_TOKEN not configured")
    if not settings.voyageai_api_key:
        raise RuntimeError("VOYAGEAI_API_KEY not configured")

    q_kwargs: dict[str, Any] = {"url": settings.qdrant_url}
    if settings.qdrant_api_key:
        q_kwargs["api_key"] = settings.qdrant_api_key
    qdrant = QdrantClient(**q_kwargs)
    ensure_collection(qdrant)

    async with httpx.AsyncClient(timeout=120.0) as client:
        pages = await list_all_pages(client)
        logger.info("Ingestion: listed %s pages", len(pages))

        current_ids: set[str] = set()
        points_batch: list[qm.PointStruct] = []

        for p in pages:
            pid = p.get("id")
            if pid is None:
                continue
            page_id = int(pid)
            full = await get_page_content(client, page_id)
            if not full:
                continue
            path = full.get("path") or ""
            title = full.get("title") or ""
            content = full.get("content") or ""
            if not content.strip():
                continue

            current_ids.add(str(page_id))

            # Remove old vectors for this page
            try:
                qdrant.delete(
                    collection_name=settings.qdrant_collection,
                    points_selector=qm.Filter(
                        must=[
                            qm.FieldCondition(
                                key="page_id",
                                match=qm.MatchValue(value=str(page_id)),
                            )
                        ]
                    ),
                )
            except Exception as e:
                logger.warning("Delete old chunks for page %s: %s", page_id, e)

            chunks = split_into_chunks(content)
            if not chunks:
                continue
            vectors = embed_texts_voyage(chunks, input_type="document")
            for idx, (vec, ch) in enumerate(zip(vectors, chunks)):
                payload = {
                    "page_id": str(page_id),
                    "page_title": title,
                    "page_path": path,
                    "chunk_index": idx,
                    "content": ch,
                }
                points_batch.append(
                    qm.PointStruct(id=_point_uuid(page_id, idx), vector=vec, payload=payload)
                )

            # upsert in batches
            if len(points_batch) >= 64:
                qdrant.upsert(collection_name=settings.qdrant_collection, points=points_batch)
                points_batch.clear()

        if points_batch:
            qdrant.upsert(collection_name=settings.qdrant_collection, points=points_batch)

        # Optional: remove stale pages (present in Qdrant but not in wiki list)
        try:
            page_ids_in_wiki = {str(p.get("id")) for p in pages if p.get("id") is not None}
            offset = None
            stale_ids: list[Any] = []
            while True:
                records, offset = qdrant.scroll(
                    collection_name=settings.qdrant_collection,
                    limit=256,
                    offset=offset,
                    with_payload=True,
                    with_vectors=False,
                )
                if not records:
                    break
                for r in records:
                    pl = r.payload or {}
                    pid = pl.get("page_id")
                    if pid and pid not in page_ids_in_wiki:
                        stale_ids.append(r.id)
                if offset is None:
                    break
            for i in range(0, len(stale_ids), 256):
                batch = stale_ids[i : i + 256]
                qdrant.delete(
                    collection_name=settings.qdrant_collection,
                    points_selector=batch,
                )
        except Exception as e:
            logger.warning("Stale cleanup skipped: %s", e)

    return {"pages_indexed": len(pages), "status": "ok"}


def schedule_ingestion_loop() -> None:
    async def _loop():
        while True:
            await asyncio.sleep(settings.ingest_interval_seconds)
            try:
                await run_ingestion_once()
            except Exception:
                logger.exception("Scheduled ingestion failed")

    asyncio.create_task(_loop())
