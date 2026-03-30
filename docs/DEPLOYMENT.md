# SmartWiki deployment guide

## CI (GitHub Actions)

On every push and pull request to `main` / `master`, [`.github/workflows/ci.yml`](../.github/workflows/ci.yml):

1. Installs **[uv](https://docs.astral.sh/uv/)** and Python 3.12.
2. Runs **`uv lock --check`** so `uv.lock` matches `pyproject.toml`.
3. Runs **`uv sync --frozen --all-groups`** for a reproducible dev environment.
4. Runs **`uv run pytest tests/unit`**.
5. Builds **Docker** images for `wiki-organizer` and `chatbot-api` (no registry push unless you extend the workflow).

Use **workflow_dispatch** in the Actions tab to run the pipeline manually.

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
