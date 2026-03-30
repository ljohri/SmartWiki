# Enhancement: React application on top of SmartWiki

SmartWiki is **API-first**. The Wiki.js-embedded HTML/JS is a thin client. You can add a **Vite + React 18** (or Next.js) app later without changing core service contracts.

## When to add React

- Compliance review workflows (queues, approvals, redaction previews).
- Admin dashboards over `submissions_log` (add read-only API or Metabase).
- Batch uploads with richer validation.
- Cross-wiki search / analytics.

## Proposed frontend layout

```
frontend/
  src/
    api/client.ts       # fetch wrappers for organizer + chatbot
    pages/
    components/
  vite.config.ts
  Dockerfile            # nginx or `vite preview` for dev only
```

## API contract (existing)

Base URLs are configurable (`ORGANIZER_PUBLIC_URL`, `CHATBOT_PUBLIC_URL`).

### Organizer

`POST /api/submit` — `multipart/form-data`

| Field | Type | Required |
|-------|------|----------|
| `title` | string | yes |
| `category` | string | yes |
| `tags` | string | no |
| `description` | string | no |
| `username` | string | no |
| `files` | file[] | yes |

Headers: `Authorization: Bearer <ORGANIZER_API_KEY>`

Response:

```json
{
  "results": [
    {
      "success": true,
      "filename": "doc.pdf",
      "pagePath": "/docs/engineering/runbook",
      "pageUrl": "https://wiki.example.com/docs/engineering/runbook",
      "pageTitle": "Runbook",
      "ai_decision": { "targetPath": "...", "pageTitle": "...", "suggestedTags": [], "summary": "..." }
    }
  ]
}
```

### Chatbot

`POST /api/chat` — `application/json`

```json
{
  "question": "How do we rotate DB passwords?",
  "history": [
    { "role": "user", "content": "..." },
    { "role": "assistant", "content": "..." }
  ]
}
```

Headers: `Authorization: Bearer <CHATBOT_API_KEY>`

Response:

```json
{
  "answer": "markdown...",
  "sources": [
    { "title": "Security", "path": "/docs/engineering/security", "url": "https://wiki.../docs/engineering/security" }
  ]
}
```

`POST /api/ingest` — admin-only reindex (same auth as chat).

## Authentication patterns

**Option A — Proxy (best):** React app is same-site; nginx injects service API keys server-side.

**Option B — User JWT:** If Wiki.js exposes a JWT or session cookie your gateway trusts, forward `Authorization: Bearer <user>` and extend FastAPI services to validate Wiki.js tokens (future work).

**Option C — SSO:** Use your IdP (OIDC) for the React app only; backend services stay key-protected behind VPC.

## Docker Compose addition

```yaml
  frontend:
    build: ./frontend
    ports:
      - "5173:80"
    environment:
      VITE_ORGANIZER_URL: http://localhost:3001
      VITE_CHATBOT_URL: http://localhost:3002
```

For production, build static assets to **Cloud Storage + Cloud CDN** or serve from the same nginx as Wiki.js.

## Cloud Run

- Separate Cloud Run service `smartwiki-ui` serving static files.
- Configure IAP or OAuth2 proxy in front.

## Compliance note

React does **not** automatically improve compliance. Pair UI features with:

- Audit logging (already on organizer via `submissions_log`).
- Data retention policies on Postgres/Qdrant.
- Access reviews for API keys and Wiki.js groups.
