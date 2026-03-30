"""Shared pytest fixtures."""

from __future__ import annotations

import os

import pytest


def pytest_configure(config):
    config.addinivalue_line("markers", "integration: requires Docker services / external URLs")
    config.addinivalue_line("markers", "e2e: Playwright browser tests against full stack")


def pytest_runtest_setup(item):
    if item.get_closest_marker("integration") and os.environ.get("INTEGRATION_TESTS") != "1":
        pytest.skip("Set INTEGRATION_TESTS=1 to run integration tests")
    if item.get_closest_marker("e2e") and os.environ.get("RUN_E2E") != "1":
        pytest.skip("Set RUN_E2E=1 to run Playwright E2E tests")


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture(autouse=True)
def _test_env(monkeypatch):
    monkeypatch.setenv("ORGANIZER_API_KEY", "test-organizer-key")
    monkeypatch.setenv("CHATBOT_API_KEY", "test-chatbot-key")
    monkeypatch.setenv("WIKIJS_API_TOKEN", "test-wiki-token")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-anthropic")
    monkeypatch.setenv("VOYAGEAI_API_KEY", "test-voyage")
    monkeypatch.setenv(
        "DATABASE_URL",
        os.environ.get("DATABASE_URL", "postgresql://wikijs:changeme@localhost:5432/wikijs"),
    )
