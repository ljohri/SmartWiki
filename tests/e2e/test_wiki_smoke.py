"""E2E smoke against Wiki.js (full docker-compose). Set RUN_E2E=1 and PLAYWRIGHT_BASE_URL."""

from __future__ import annotations

import os

import pytest
from playwright.sync_api import Page, expect

pytestmark = [pytest.mark.e2e]


@pytest.fixture(scope="session")
def base_url():
    return os.environ.get("PLAYWRIGHT_BASE_URL", "http://127.0.0.1:3000")


def test_wiki_home_loads(page: Page, base_url: str):
    page.goto(base_url, wait_until="domcontentloaded", timeout=60_000)
    # Setup wizard or login — page should render something
    expect(page.locator("body")).to_be_visible()
