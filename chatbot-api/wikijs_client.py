"""Wiki.js GraphQL helpers for chatbot ingestion."""

from __future__ import annotations

import json
from typing import Any

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from config import settings


class WikiJsError(Exception):
    pass


def _headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {settings.wikijs_api_token}",
        "Content-Type": "application/json",
    }


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10))
async def graphql(client: httpx.AsyncClient, query: str, variables: dict[str, Any] | None = None) -> dict[str, Any]:
    payload: dict[str, Any] = {"query": query}
    if variables is not None:
        payload["variables"] = variables
    r = await client.post(settings.wikijs_graphql_url, json=payload, headers=_headers())
    r.raise_for_status()
    body = r.json()
    if body.get("errors"):
        raise WikiJsError(json.dumps(body["errors"]))
    return body.get("data") or {}


async def list_all_pages(client: httpx.AsyncClient, limit: int = 5000) -> list[dict[str, Any]]:
    query = """
    query ListPages($limit: Int!, $locale: String!) {
      pages {
        list(orderBy: PATH, orderByDirection: ASC, limit: $limit, locale: $locale) {
          id
          path
          title
        }
      }
    }
    """
    data = await graphql(client, query, {"limit": limit, "locale": settings.wikijs_locale})
    return (data.get("pages") or {}).get("list") or []


async def get_page_content(client: httpx.AsyncClient, page_id: int) -> dict[str, Any] | None:
    query = """
    query PageSingle($id: Int!) {
      pages {
        single(id: $id) {
          id
          path
          title
          content
        }
      }
    }
    """
    data = await graphql(client, query, {"id": page_id})
    return (data.get("pages") or {}).get("single")
