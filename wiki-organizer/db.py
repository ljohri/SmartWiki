"""Postgres audit log for submissions."""

from __future__ import annotations

import json
from typing import Any

import asyncpg

from config import settings


async def log_submission(
    pool: asyncpg.Pool,
    *,
    username: str,
    title: str,
    category: str,
    tags: list[str],
    original_filename: str,
    target_path: str | None,
    ai_decision: dict[str, Any] | None,
    status: str,
    error_message: str | None = None,
) -> None:
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO submissions_log
              (username, title, category, tags, original_filename, target_path, ai_decision, status, error_message, updated_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7::jsonb, $8, $9, NOW())
            """,
            username,
            title,
            category,
            tags,
            original_filename,
            target_path,
            json.dumps(ai_decision) if isinstance(ai_decision, dict) else None,
            status,
            error_message,
        )


async def create_pool() -> asyncpg.Pool:
    return await asyncpg.create_pool(settings.database_url, min_size=1, max_size=5)
