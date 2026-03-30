"""Wiki.js 2.x GraphQL client."""

from __future__ import annotations

import json
from typing import Any

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from config import settings


class WikiJsAPIError(Exception):
    pass


def _headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {settings.wikijs_api_token}",
        "Content-Type": "application/json",
    }


class WikiJsGraphQL:
    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        self._own_client = client is None
        self._client = client or httpx.AsyncClient(timeout=60.0)

    async def aclose(self) -> None:
        if self._own_client:
            await self._client.aclose()

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10))
    async def _post(self, payload: dict[str, Any]) -> dict[str, Any]:
        r = await self._client.post(settings.wikijs_graphql_url, json=payload, headers=_headers())
        r.raise_for_status()
        body = r.json()
        if "errors" in body and body["errors"]:
            raise WikiJsAPIError(json.dumps(body["errors"]))
        return body.get("data") or {}

    async def get_page_tree_text(self) -> str:
        """Return a human-readable tree for the organizer prompt."""
        query = """
        query PageTree($locale: String!) {
          pages {
            tree(path: "/", mode: ALL, locale: $locale) {
              id
              path
              title
              depth
              isFolder
            }
          }
        }
        """
        try:
            data = await self._post(
                {"query": query, "variables": {"locale": settings.wikijs_locale}}
            )
            items = (data.get("pages") or {}).get("tree") or []
        except WikiJsAPIError:
            items = []

        if not items:
            # Fallback: flat list of paths
            q2 = """
            query PageList($limit: Int!, $locale: String!) {
              pages {
                list(orderBy: PATH, limit: $limit, locale: $locale) {
                  path
                  title
                }
              }
            }
            """
            data2 = await self._post(
                {"query": q2, "variables": {"limit": 2000, "locale": settings.wikijs_locale}}
            )
            rows = (data2.get("pages") or {}).get("list") or []
            lines = [f"[page] {r.get('path')} — {r.get('title')}" for r in rows]
            return "\n".join(lines) if lines else "(empty wiki)"

        lines: list[str] = []
        for it in sorted(items, key=lambda x: (x.get("path") or "")):
            depth = int(it.get("depth") or 0)
            indent = "  " * depth
            kind = "folder" if it.get("isFolder") else "page"
            lines.append(f"{indent}[{kind}] {it.get('path')} — {it.get('title')}")
        return "\n".join(lines) if lines else "(empty wiki)"

    async def get_page_by_path(self, path: str) -> dict[str, Any] | None:
        query = """
        query PageByPath($path: String!, $locale: String!) {
          pages {
            singleByPath(path: $path, locale: $locale) {
              id
              path
              title
              description
              content
              tags { tag }
            }
          }
        }
        """
        data = await self._post(
            {"query": query, "variables": {"path": path, "locale": settings.wikijs_locale}}
        )
        page = (data.get("pages") or {}).get("singleByPath")
        return page

    async def create_page(
        self,
        *,
        path: str,
        title: str,
        content: str,
        tags: list[str],
        description: str = "",
    ) -> dict[str, Any]:
        mutation = """
        mutation CreatePage(
          $content: String!
          $description: String!
          $editor: String!
          $isPublished: Boolean!
          $isPrivate: Boolean!
          $locale: String!
          $path: String!
          $tags: [String]!
          $title: String!
        ) {
          pages {
            create(
              content: $content
              description: $description
              editor: $editor
              isPublished: $isPublished
              isPrivate: $isPrivate
              locale: $locale
              path: $path
              tags: $tags
              title: $title
            ) {
              responseResult { succeeded errorCode slug message }
              page { id path title }
            }
          }
        }
        """
        variables = {
            "content": content,
            "description": description or title,
            "editor": "markdown",
            "isPublished": True,
            "isPrivate": False,
            "locale": settings.wikijs_locale,
            "path": path,
            "tags": tags,
            "title": title,
        }
        data = await self._post({"query": mutation, "variables": variables})
        return (data.get("pages") or {}).get("create") or {}

    async def update_page(
        self,
        *,
        page_id: int,
        content: str | None = None,
        title: str | None = None,
        tags: list[str] | None = None,
        description: str | None = None,
    ) -> dict[str, Any]:
        mutation = """
        mutation UpdatePage(
          $id: Int!
          $content: String
          $title: String
          $tags: [String]
          $description: String
        ) {
          pages {
            update(id: $id, content: $content, title: $title, tags: $tags, description: $description) {
              responseResult { succeeded errorCode slug message }
              page { id path title }
            }
          }
        }
        """
        variables: dict[str, Any] = {"id": page_id}
        if content is not None:
            variables["content"] = content
        if title is not None:
            variables["title"] = title
        if tags is not None:
            variables["tags"] = tags
        if description is not None:
            variables["description"] = description
        data = await self._post({"query": mutation, "variables": variables})
        return (data.get("pages") or {}).get("update") or {}
