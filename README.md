# Support2Fix

Support2Fix is an AI platform that turns a customer support issue into an evidence-backed engineering investigation. The flow runs: root cause → reproduction → validated fix → human-approved pull request → customer response.

> **Status: Phase 1 (project foundation).** The Next.js and FastAPI apps run and are tested. Tickets, auth, agents and everything else land in later phases — see the roadmap in [ADR-001](docs/decisions/001-architecture.md).

## Architecture documents

- [System design](docs/architecture/system-design.md): components, data flow, data model, API boundaries, integrations, failure handling, deployment
- [Agent architecture](docs/architecture/agent-architecture.md): LangGraph workflow, MCP ToolGateway, evidence and grounding, LLM layer
- [Security model](docs/architecture/security.md): threat model, RBAC, tool permissions, prompt-injection defenses, sandbox isolation
- [ADR-001: Initial architecture](docs/decisions/001-architecture.md): decisions, alternatives, risks, resolved questions

## Stack

Next.js 16 · React 19 · TypeScript · Tailwind CSS 4 · FastAPI · Pydantic v2 · SQLAlchemy 2 (async) · Alembic · LangGraph · MCP · PostgreSQL + pgvector · Docker Compose · GitHub Actions · AWS-compatible deployment

## Repository layout

```text
apps/
  api/   FastAPI backend (also the worker / tools / sandbox-runner entrypoints, added in later phases)
  web/   Next.js frontend
docs/    architecture, decisions
infrastructure/docker/   Dockerfiles used by docker-compose.yml
```

## Running locally

### Option A — Docker Compose (recommended once Docker is installed)

Requires Docker Desktop (WSL2 backend on Windows).

```bash
cp .env.example .env
docker compose up --build
```

- Frontend: http://localhost:3000
- API: http://localhost:8000 (docs at `/docs`)
- Postgres: `localhost:5432` (user/password/db: `support2fix` by default)

### Option B — Run the apps directly (no Docker)

Two terminals, from the repo root.

**API** (needs Python 3.11+; a local Postgres, or just accept a "degraded" health check — see below):

```bash
cd apps/api
python -m venv .venv
./.venv/Scripts/pip install -e ".[dev]"   # macOS/Linux: source .venv/bin/activate first
./.venv/Scripts/python -m uvicorn app.main:app --reload --port 8000
```

**Web:**

```bash
cd apps/web
npm install
npm run dev
```

Then open http://localhost:3000/dashboard. The Next.js dev server proxies `/api/*` to `http://localhost:8000` (configurable via `API_ORIGIN`), so no CORS setup is needed — see [ADR-001 D10](docs/decisions/001-architecture.md).

### Health checks

- `GET /health` — liveness only, no dependency checks.
- `GET /api/v1/health` — checks the database. Returns `503 {"status": "degraded", "database": "unreachable"}` instead of crashing when Postgres isn't reachable, which is expected if you're running Option B without a local Postgres. The dashboard's status pill reflects this.

## Testing and quality checks

**API:**

```bash
cd apps/api
./.venv/Scripts/python -m pytest -q
./.venv/Scripts/python -m ruff check .
./.venv/Scripts/python -m ruff format --check .
./.venv/Scripts/python -m mypy app
```

**Web:**

```bash
cd apps/web
npm run test        # vitest
npm run typecheck   # tsc --noEmit
npm run lint        # eslint
npm run format      # prettier --check
npm run build       # production build
```

All of the above are green as of Phase 1, without a running Postgres (the API tests exercise the graceful-degradation path directly).

## Environment variables

See [.env.example](.env.example). Nothing is required to run Phase 1 — the API defaults to a local Postgres URL and `LLM_MODE=fake`, so it starts even without a database or an LLM API key.
