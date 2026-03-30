# SmartWiki

Private **community wiki** stack: [Wiki.js](https://js.wiki/) **2.x**, **FastAPI** services for AI document filing (Anthropic Claude) and a **RAG chatbot** (Claude + **Voyage AI** embeddings + **Qdrant**). Submission UI and chat widget are **embedded in Wiki.js** (HTML/JS assets).

- **Open source code** lives in this repository.
- **Wiki content** stays private (Docker volumes, your network, optional enterprise git backup)—not committed here.

## Architecture

```mermaid
graph TB
  subgraph stack [Docker Compose]
    PG[(PostgreSQL)]
    W[Wiki.js :3000]
    Q[Qdrant :6333]
    O[Organizer FastAPI :3001]
    C[Chatbot FastAPI :3002]
  end
  U[Browser] --> W
  W --> O
  W --> C
  O --> W
  O --> PG
  C --> W
  C --> Q
  W --> PG
```

| Service        | Role |
|----------------|------|
| `postgres`     | Wiki.js DB + `submissions_log` audit table |
| `wiki`         | Wiki.js 2.x UI & content |
| `qdrant`       | Vector index for RAG chunks |
| `organizer`    | Multipart upload → Claude classification → Wiki.js GraphQL create/update |
| `chatbot`      | Embed question (Voyage) → Qdrant search → Claude answer (+ optional web search) |

See **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)** for detail.

## Prerequisites

- Docker & Docker Compose
- [Anthropic API key](https://console.anthropic.com/) (Claude)
- [Voyage AI API key](https://www.voyageai.com/) (embeddings; model default `voyage-4`, 1024 dims)
- **Python 3.12** recommended for local tests (see `.python-version`)
- **[uv](https://docs.astral.sh/uv/)** for the dev virtualenv (lockfile-driven; same as CI)

## Quick start

1. **Clone & configure**

   ```bash
   cd SmartWiki
   cp .env.example .env
   # Edit .env: POSTGRES_PASSWORD, ORGANIZER_API_KEY, CHATBOT_API_KEY, ANTHROPIC_API_KEY, VOYAGEAI_API_KEY
   ```

2. **Start stack**

   ```bash
   docker compose up -d
   ```

3. **Complete Wiki.js setup** at [http://localhost:3000](http://localhost:3000)

   - Database: host `postgres`, port `5432`, DB/user/password from `.env`
   - Enable **Local** auth only; lock down guest access (see plan / `docs/DEPLOYMENT.md`)
   - **Admin → API Access**: create token with scopes including **read/write pages** and **read page source** (for ingestion). Put token in `.env` as `WIKIJS_API_TOKEN`.

4. **Restart** services that need the token:

   ```bash
   docker compose restart organizer chatbot
   ```

5. **Trigger ingestion** (indexes wiki into Qdrant):

   ```bash
   curl -sS -X POST http://localhost:3002/api/ingest \
     -H "Authorization: Bearer YOUR_CHATBOT_API_KEY"
   ```

6. **Embed UI**

   - Copy `wiki-assets/submit-form.html` into a Wiki.js page at `/submit` (HTML editor). Set `SMARTWIKI_CONFIG` (URLs + `ORGANIZER_API_KEY`).
   - Inject `chat-widget.css`, `marked.min.js`, and `chat-widget.js` via **Admin → Theme → Code Injection**; set `SMARTWIKI_CHAT_CONFIG`. See `wiki-assets/README.md`.

## Configuration (environment)

| Variable | Purpose |
|----------|---------|
| `DATABASE_URL` | Organizer → Postgres (`submissions_log`) |
| `WIKIJS_GRAPHQL_URL` | Usually `http://wiki:3000/graphql` in Compose |
| `WIKIJS_API_TOKEN` | Bearer token for Wiki.js GraphQL |
| `WIKIJS_LOCALE` | e.g. `en` (tree/list queries) |
| `ORGANIZER_API_KEY` | Clients must send `Authorization: Bearer …` to `POST /api/submit` |
| `CHATBOT_API_KEY` | Same for `/api/chat` and `/api/ingest` |
| `ANTHROPIC_API_KEY` / `ANTHROPIC_MODEL` | Claude (default model in `.env.example` is a current Sonnet id—set your allowed model) |
| `VOYAGEAI_API_KEY` / `VOYAGE_EMBEDDING_*` | Embeddings |
| `QDRANT_URL` / `QDRANT_API_KEY` / `QDRANT_COLLECTION` | Vector DB |
| `CORS_ORIGINS` | Allowed browser origins (Compose passes `WIKI_PUBLIC_URL`) |
| `INGEST_INTERVAL_SECONDS` | Background re-ingest (default 6h) |
| `CHAT_RATE_LIMIT_PER_MINUTE` | SlowAPI limit per IP |

## API summary

| Endpoint | Service | Auth |
|----------|---------|------|
| `GET /api/health` | organizer, chatbot | none |
| `POST /api/submit` | organizer | Bearer `ORGANIZER_API_KEY` |
| `POST /api/chat` | chatbot | Bearer `CHATBOT_API_KEY` |
| `POST /api/ingest` | chatbot | Bearer `CHATBOT_API_KEY` |

## Tests (uv)

The repo root [`pyproject.toml`](pyproject.toml) + [`uv.lock`](uv.lock) define a **single dev environment** (organizer + chatbot + test deps). Docker images still install from each service’s `requirements.txt`.

```bash
# Install uv: https://docs.astral.sh/uv/getting-started/installation/
cd SmartWiki
uv sync --all-groups          # creates .venv and installs locked deps
uv run pytest tests/unit -v
```

After changing dependencies in `pyproject.toml`, refresh the lockfile and commit it:

```bash
uv lock
```

GitHub Actions (`.github/workflows/ci.yml`) runs `uv lock --check`, `uv sync --frozen --all-groups`, and `uv run pytest tests/unit` on every push/PR.

- **Integration** (health checks against running stack):

  ```bash
  export INTEGRATION_TESTS=1
  uv run pytest tests/integration -v
  ```

- **E2E** (Playwright; full stack):

  ```bash
  export RUN_E2E=1
  uv run playwright install chromium
  uv run pytest tests/e2e -v
  ```

See `.env.test.example` and `tests/docker-compose.test.yml`.

## Documentation

- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — components & data flows  
- [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) — production & hardening  
- [docs/ENHANCEMENT-CLOUDRUN.md](docs/ENHANCEMENT-CLOUDRUN.md) — Google Cloud Run playbook  
- [docs/ENHANCEMENT-REACT.md](docs/ENHANCEMENT-REACT.md) — optional React app on top  

## Wiki.js 3.x

Wiki.js 3.x is still **non-production** for many orgs. This repo targets **2.x** GraphQL shapes; when 3.x is stable, revisit `wikijs_api.py`, `wikijs_client.py`, and image tags.

## License

MIT — see [LICENSE](LICENSE).
