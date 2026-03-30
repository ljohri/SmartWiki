"""Qdrant connectivity (optional integration)."""

from __future__ import annotations

import os

import pytest
from qdrant_client import QdrantClient

pytestmark = pytest.mark.integration


def test_qdrant_ping():
    url = os.environ.get("QDRANT_URL", "http://127.0.0.1:6333")
    client = QdrantClient(url=url)
    cols = client.get_collections()
    assert cols is not None
