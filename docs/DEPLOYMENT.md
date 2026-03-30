# SmartWiki deployment guide

## CI/CD (GitHub Actions)

[`.github/workflows/ci.yml`](../.github/workflows/ci.yml) implements the full pipeline:

**Continuous integration**

1. **[uv](https://docs.astral.sh/uv/)** + Python 3.12.
2. **`uv lock --check`** — lockfile matches `pyproject.toml`.
3. **`uv sync --frozen --all-groups`** — reproducible env.
4. **`uv run pytest tests/unit`**.

**Continuous delivery (container images)**

- **Pull requests**: Docker images are **built only** (validates Dockerfiles); nothing is pushed (avoids leaking registry tokens on fork PRs).
- **Push** to `main` / `master`: images are pushed to **GitHub Container Registry** (`ghcr.io`):
  - `ghcr.io/<owner>/smartwiki-organizer` — tags `main`, `sha-<short>`, …
  - `ghcr.io/<owner>/smartwiki-chatbot` — same pattern.
- **Git tag** `v*` (e.g. `v1.2.0`): same images also get **version** and **`latest`** tags.
- **workflow_dispatch**: re-run from the Actions tab to rebuild and **push** for the chosen branch.

**Post-setup**

- In GitHub → **Packages**, set each package’s **visibility** and connect it to the repository if desired.
- Deploy by pointing your runtime (Compose override, Kubernetes, Cloud Run, etc.) at the GHCR digests or tags you trust.

## Local / single-server (Docker Compose)

1. Copy `.env.example` → `.env`; set strong passwords and API keys.
2. `docker compose up -d`
3. Finish Wiki.js wizard; set **API token** with scopes: read/write pages, read page source (for ingestion).
4. `docker compose restart organizer chatbot`
5. `curl -X POST http://localhost:3002/api/ingest -H "Authorization: Bearer $CHATBOT_API_KEY"`
6. Embed `wiki-assets/*` per `wiki-assets/README.md`.

### Reverse proxy (recommended)

Put **Wiki.js**, **organizer**, and **chatbot** behind one hostname (e.g. `wiki.company.com`, `/api/organizer`, `/api/chat`) so:

- Cookies/sessions behave predictably.
- You can **strip** browser-exposed API keys and inject `Authorization` via nginx/Envoy.

Example pattern (nginx):

```nginx
location /api/organizer/ {
  proxy_pass http://127.0.0.1:3001/;
  proxy_set_header Authorization "Bearer $organizer_upstream_secret";
}
```

Map `$organizer_upstream_secret` from a file or environment — **not** from the client.

## Virtual machine (e.g. GCE)

- Install Docker Engine + Compose plugin (or use Container-Optimized OS patterns).
- Attach persistent disks or use managed **Persistent Disk** for `./data/postgres`, `./data/wiki`, `./data/qdrant`.
- Use **systemd** unit to run `docker compose up -d` on boot.
- Terminate TLS at **Google Cloud Load Balancing** or **nginx + certbot**.

## Backups

| Asset | Approach |
|-------|----------|
| PostgreSQL | `pg_dump` of `wikijs` DB on schedule; test restores quarterly |
| Wiki.js files | Backup `./data/wiki` volume |
| Qdrant | Snapshot `./data/qdrant` or use Qdrant backup APIs / managed offering |
| Secrets | Store in Secret Manager / Vault; rotate API keys |

## Monitoring

- Hit `GET /api/health` on organizer and chatbot from your monitor.
- Track container restarts, CPU/memory, disk usage.
- Log shipping: JSON logs from uvicorn → Cloud Logging / ELK.

## Hardening checklist

- [ ] Strong `POSTGRES_PASSWORD`, `ORGANIZER_API_KEY`, `CHATBOT_API_KEY`, `WIKIJS_API_TOKEN`
- [ ] Wiki.js: disable guest; enforce MFA if available
- [ ] Firewall: only 443 (and admin SSH) exposed
- [ ] CORS locked to your wiki origin
- [ ] Rate limits tuned (`CHAT_RATE_LIMIT_PER_MINUTE`)
- [ ] Regular dependency & image updates (`ghcr.io/requarks/wiki:2`, base Python images)

## Cloud Run

See **[ENHANCEMENT-CLOUDRUN.md](ENHANCEMENT-CLOUDRUN.md)** for service-by-service mapping, Cloud SQL, and Qdrant options.
