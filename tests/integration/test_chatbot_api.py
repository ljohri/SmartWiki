"""Integration: chatbot health (requires stack)."""

from __future__ import annotations

import os

import httpx
import pytest

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_chatbot_health():
    base = os.environ.get("CHATBOT_URL", "http://127.0.0.1:3002")
    async with httpx.AsyncClient(base_url=base, timeout=10.0) as client:
        r = await client.get("/api/health")
    assert r.status_code == 200
    assert r.json().get("service") == "chatbot-api"
