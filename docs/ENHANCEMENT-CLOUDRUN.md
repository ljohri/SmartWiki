# Enhancement: Google Cloud Run deployment

Compose is ideal for dev/single VM. **Cloud Run** is request-scaled HTTP services without persistent local disk by default. Below is a practical mapping.

## Target architecture

| Compose service | Cloud Run suggestion |
|-----------------|----------------------|
| `postgres` | **Cloud SQL for PostgreSQL** (private IP + VPC connector) |
| `wiki` | Cloud Run service **or** GCE VM if Wiki.js needs long-lived local disk semantics |
| `qdrant` | **Qdrant Managed Cloud** on GCP Marketplace **or** Cloud Run + **Filestore** / **GCS FUSE** (advanced) |
| `organizer` | Cloud Run service (stateless) |
| `chatbot` | Cloud Run service (stateless); ingestion as **Cloud Scheduler → HTTP** to `/api/ingest` |

**Note:** Wiki.js expects writable `/wiki/data`. For pure Cloud Run you typically need a shared filesystem, or run Wiki.js on a **VM** / **GKE** with a PVC. Many teams keep Wiki.js on a **small GCE instance** with Compose while moving AI services to Cloud Run.

## Networking

- **VPC Serverless Connector** from Cloud Run to Cloud SQL private IP.
- **IAM**: Cloud Run service accounts; avoid long-lived keys in containers—use **Workload Identity** where possible.
- **Ingress**: internal-only + IAP, or public HTTPS with Cloud Load Balancing.

## Secrets

- **Google Secret Manager** for `ANTHROPIC_API_KEY`, `VOYAGEAI_API_KEY`, `WIKIJS_API_TOKEN`, `ORGANIZER_API_KEY`, `CHATBOT_API_KEY`.
- Mount as env vars in Cloud Run revision.

## Container images

- Build with **Cloud Build** on push to `main`:
  - `gcr.io/$PROJECT/smartwiki-organizer:$SHORT_SHA`
  - `gcr.io/$PROJECT/smartwiki-chatbot:$SHORT_SHA`
- Deploy two Cloud Run services with different ports/env.

## Environment variables (Cloud Run)

Mirror `.env.example` but replace hostnames:

- `DATABASE_URL` → Cloud SQL DSN (via connector or proxy sidecar pattern).
- `WIKIJS_GRAPHQL_URL` → public or internal URL of Wiki.js `/graphql`.
- `QDRANT_URL` → HTTPS endpoint of managed Qdrant cluster.
- `WIKI_PUBLIC_URL`, `CORS_ORIGINS` → your user-facing wiki origin.

## Ingestion on Cloud Run

Long-running background loops inside a Cloud Run instance are **fragile** (instances scale to zero). Prefer:

- **Cloud Scheduler** → authenticated `POST /api/ingest` every N hours.
- Optional Wiki.js **webhook** (future enhancement) on publish → ingest.

## Cost levers

- Cloud Run min instances = 0 for dev; 1+ for low cold-start latency on chat.
- Cloud SQL: start small; enable HA for prod.
- Qdrant Managed: pick tier by vector count & QPS.

## IaC

- **Terraform / Pulumi** modules recommended for: VPC connector, Cloud SQL, Secret Manager, Artifact Registry, Cloud Run services, Scheduler jobs.
- Keep this repository **code-only**; store env-specific tfvars outside git.

## GCS and Qdrant

- **GCS** is object storage; Qdrant persists **indexes** on block storage. Typical patterns:
  - **Qdrant Managed** (GCP) — easiest ops.
  - **Self-hosted Qdrant on Cloud Run** — requires durable volume (Filestore mount) and careful scaling (often single-instance).

This project’s default **Compose** Qdrant volume maps to `./data/qdrant` for local durability.
