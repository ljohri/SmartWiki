"""Claude-based classification and Wiki.js page create/update."""

from __future__ import annotations

import json
import re
from typing import Any

import anthropic
from pydantic import BaseModel, Field, field_validator

from config import settings
from file_parser import FileParseError, extract_text
from wikijs_api import WikiJsAPIError, WikiJsGraphQL


class OrganizerDecision(BaseModel):
    targetPath: str
    pageTitle: str
    suggestedTags: list[str] = Field(default_factory=list)
    summary: str = ""

    @field_validator("targetPath")
    @classmethod
    def normalize_path(cls, v: str) -> str:
        p = v.strip()
        if not p.startswith("/"):
            p = "/" + p
        return p


EXCERPT_MAX_CHARS = 12000  # ~3k tokens rough budget


def _parse_json_from_claude(text: str) -> dict[str, Any]:
    text = text.strip()
    m = re.search(r"\{[\s\S]*\}\s*$", text)
    if not m:
        raise ValueError("No JSON object in model response")
    return json.loads(m.group(0))


def build_organizer_prompt(
    *,
    wiki_tree: str,
    title: str,
    category: str,
    tags: str,
    description: str,
    content_excerpt: str,
) -> str:
    return f"""You are a wiki content organizer. Given a document and the current wiki structure, decide where this document should be filed.

Current wiki structure:
{wiki_tree}

Document metadata:
- Title: {title}
- User category: {category}
- Tags: {tags}
- Description: {description}

Document content (excerpt):
{content_excerpt}

Respond ONLY with a JSON object (no markdown fences, no explanation):
{{
  "targetPath": "/docs/engineering/example-topic",
  "pageTitle": "Clear Descriptive Title",
  "suggestedTags": ["tag-one", "tag-two"],
  "summary": "Two-sentence summary of the document."
}}

Rules:
- targetPath must be under /docs/{{category_slug}}/ or a relevant subpath (category_slug is lowercase: engineering, product, hr, legal, general).
- Use lowercase-hyphenated path segments.
- If a relevant subfolder does not exist in the tree, still choose a logical path under /docs/...
- pageTitle should be clean and descriptive.
"""


async def classify_with_claude(
    client: anthropic.Anthropic,
    *,
    wiki_tree: str,
    title: str,
    category: str,
    tags: str,
    description: str,
    content: str,
) -> OrganizerDecision:
    excerpt = content[:EXCERPT_MAX_CHARS]
    prompt = build_organizer_prompt(
        wiki_tree=wiki_tree,
        title=title,
        category=category,
        tags=tags,
        description=description,
        content_excerpt=excerpt,
    )
    msg = client.messages.create(
        model=settings.anthropic_model,
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )
    text_parts: list[str] = []
    for block in msg.content:
        if block.type == "text":
            text_parts.append(block.text)
    raw = "\n".join(text_parts)
    data = _parse_json_from_claude(raw)
    return OrganizerDecision.model_validate(data)


def build_markdown_page(
    *,
    original_filename: str,
    user_title: str,
    summary: str,
    body: str,
    category: str,
    user_tags: str,
) -> str:
    meta = f"""---
title: {user_title}
original_file: {original_filename}
category: {category}
user_tags: {user_tags}
---

## Summary

{summary}

## Original content

{body}
"""
    return meta


async def process_single_file(
    *,
    wiki: WikiJsGraphQL,
    anthropic_client: anthropic.Anthropic,
    filename: str,
    raw_bytes: bytes,
    title: str,
    category: str,
    tags: str,
    description: str,
    username: str,
) -> dict[str, Any]:
    try:
        body_text = extract_text(filename, raw_bytes)
    except FileParseError as e:
        return {"success": False, "filename": filename, "error": str(e)}

    wiki_tree = await wiki.get_page_tree_text()
    decision = await classify_with_claude(
        anthropic_client,
        wiki_tree=wiki_tree,
        title=title,
        category=category,
        tags=tags,
        description=description,
        content=body_text,
    )

    md = build_markdown_page(
        original_filename=filename,
        user_title=title,
        summary=decision.summary,
        body=body_text,
        category=category,
        user_tags=tags,
    )
    tag_list = list(
        dict.fromkeys([t.strip() for t in decision.suggestedTags if t.strip()])
    )

    existing = await wiki.get_page_by_path(decision.targetPath)
    try:
        if existing and existing.get("id"):
            page_id = int(existing["id"])
            res = await wiki.update_page(
                page_id=page_id,
                content=md,
                title=decision.pageTitle,
                tags=tag_list,
                description=decision.summary[:500],
            )
        else:
            res = await wiki.create_page(
                path=decision.targetPath,
                title=decision.pageTitle,
                content=md,
                tags=tag_list,
                description=decision.summary[:500],
            )
    except WikiJsAPIError as e:
        return {
            "success": False,
            "filename": filename,
            "error": str(e),
            "ai_decision": decision.model_dump(),
        }

    rr = (res.get("responseResult") or {})
    if not rr.get("succeeded"):
        return {
            "success": False,
            "filename": filename,
            "error": rr.get("message") or rr.get("slug") or "Wiki.js mutation failed",
            "ai_decision": decision.model_dump(),
        }

    page = res.get("page") or {}
    path = page.get("path") or decision.targetPath
    page_url = f"{settings.wiki_public_url.rstrip('/')}{path}"
    return {
        "success": True,
        "filename": filename,
        "pagePath": path,
        "pageUrl": page_url,
        "pageTitle": decision.pageTitle,
        "ai_decision": decision.model_dump(),
    }
