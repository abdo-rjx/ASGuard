# Deployment

## Docker Compose (single command)

```bash
cp .env.example .env   # optional; compose provides dev defaults
docker compose up --build
```

- `db` — PostgreSQL 16 (ASGuard's own metadata store)
- `asguard` — FastAPI backend + built React dashboard served from one container on :8000

Open http://localhost:8000/ — the dashboard, the API and the demo mock upstream all run
behind the same port. Schema is created automatically on first start (see Migrations).

## Configuration (environment variables)

| Variable | Default | Purpose |
|---|---|---|
| `DATABASE_URL` | `postgresql+asyncpg://asguard:asguard_dev@localhost:5432/asguard` | ASGuard's own metadata DB (never an enterprise DB) |
| `SEED_DEMO_DATA` | `true` | Seed default policies + the demo application |
| `DEMO_UPSTREAM_URL` | `http://localhost:8000/demo/upstream/v1` | Mock upstream used by the demo application |
| `DETECTOR_FAILURE_MODE` | `fail_closed` | `fail_closed` (BLOCK) or `fail_open` on detector crash |
| `DEFAULT_BLOCK_THRESHOLD` | `70` | UI default; live thresholds live in the policy engine |
| `ALLOW_CONTENT_LOGGING` | `false` | Build-time kill switch for content preview logging |
| `ASGUARD_ENVIRONMENT` | `development` | `production` disables dev conveniences |
| `ASGUARD_LOG_LEVEL` | `INFO` | Root log level (all logs auto-redacted) |

Copy `.env.example` → `.env` for local runs. **Never commit real secrets** (`.env` is
git-ignored). The repository contains no credentials — the compose dev password is
explicitly a development default.

## Migrations

- **Dev/test**: tables are created with `create_all` on startup (idempotent).
- **Production**: Alembic is the source of truth.

```bash
cd backend
export DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/asguard
alembic upgrade head          # apply schema (0001_initial)
alembic revision --autogenerate -m "…"   # future schema changes
```

The initial migration matches the ORM exactly (including the
`uq_policies_direction_category` unique constraint). On an existing create_all database,
stamp once with `alembic stamp head` before switching to migrations.

## Production notes

- Serve behind TLS (nginx/traefik/caddy). ASGuard itself binds plain HTTP.
- Put authentication in front of the dashboard (`/`, `/api/*`) — SSO, mTLS or a reverse
  proxy with auth. The proxy endpoint `/v1/chat/completions` is protected by application
  API-key resolution and rate limits.
- Set `SEED_DEMO_DATA=false` to avoid creating the demo application in production.
- Back up PostgreSQL; events grow with traffic — prune `security_events` by retention
  (Settings → Privacy → retention_days documents the intent; apply your own scheduled
  pruning job at the DB level).
- Scale horizontally behind a load balancer; note the in-memory rate limiter is
  per-process until the Redis-backed limiter extension point is used.

## Health & readiness

- `GET /health` — liveness.
- `GET /ready` — readiness including a database round-trip (503 when the DB is down).

## Upgrading

1. Pull the new version.
2. `alembic upgrade head`.
3. Restart containers. Policies/applications/events survive (stored in PostgreSQL).