"""
Integration tests for organizer HTTP API (requires running organizer + postgres + wiki or mocks).

Run manually:
  docker compose up -d postgres wiki organizer
  pytest tests/integration/test_organizer_api.py -m integration
"""

from __future__ import annotations

import os

import httpx
import pytest

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_health_integration():
    base = os.environ.get("ORGANIZER_URL", "http://127.0.0.1:3001")
    async with httpx.AsyncClient(base_url=base, timeout=10.0) as client:
        r = await client.get("/api/health")
    assert r.status_code == 200
    assert r.json().get("service") == "wiki-organizer"
