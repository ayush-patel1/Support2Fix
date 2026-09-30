# ADR-001: Initial Architecture

- **Status:** Accepted (2026-09-30). Open questions resolved by the lead engineer, as delegated by the project owner.
- **Date:** 2026-09-30
- **Deciders:** Lead engineer (delegated by project owner)
- **Details:** [system-design.md](../architecture/system-design.md) · [agent-architecture.md](../architecture/agent-architecture.md) · [security.md](../architecture/security.md)

## Context

Support2Fix must turn support tickets into evidence-backed investigations, reproductions, validated fixes and human-approved PRs. It has to be secure against untrusted input (tickets, logs, code), tenant-isolated, explainable and demonstrable locally with Docker Compose. It also has to be deployable on AWS.

Constraints:

- Stack is limited to TypeScript/Next.js/React/Tailwind, Python/FastAPI/Pydantic/SQLAlchemy, LangGraph, MCP, PostgreSQL/pgvector, Docker, GitHub Actions, AWS-compatible infrastructure.
- Start as a modular monolith. Build incrementally in 25 phases, each runnable and tested.
- Never fabricate evidence, integrations or metrics.

The repository is empty at the time of this decision.

## Decisions

### D1. Modular monolith with privilege-separated runtime units

One Python codebase and image with four entrypoints (`api`, `worker`, `tools`, `sandbox-runner`), plus the Next.js `web` app and PostgreSQL. Each unit is introduced in the phase that first needs it.

- *Alternatives:* a single process for everything, which is simplest but puts credentials, LLM loops and Docker access in one blast radius. Microservices per domain add operational cost with no current benefit.
- *Rationale:* separation follows **privilege and lifetime**, not domain. The LLM-driving worker never holds integration credentials. Only the sandbox-runner can start containers.

### D2. PostgreSQL as the only stateful store

The same database holds app data, the job queue (`FOR UPDATE SKIP LOCKED` + leases + polling), LangGraph checkpoints, embeddings (pgvector, HNSW) and the audit log.

- *Alternatives:* Redis/Celery (not in the approved stack, and another stateful component), a dedicated vector database (not needed at this scale), SQS (kept as the swap target behind the `JobQueue` interface).
- *Trade-off:* the Postgres queue has lower throughput than dedicated brokers. That's acceptable for tens of concurrent investigations. Revisit with measurements.

### D3. LangGraph with a fixed graph and bounded agentic nodes

A deterministic `StateGraph` defines the stages. Tool-calling loops happen only in specific nodes, with step and budget caps. `AsyncPostgresSaver` provides durability, and `interrupt()` / `Command(resume)` handles approvals.

- *Alternatives:* one ReAct-style agent with all tools (hard to audit, unbounded, poor failure isolation). A hand-written state machine (reinvents checkpointing and resume). High-level prebuilt agent wrappers (less control over prompts, retries and accounting).
- *Consequence:* nodes must tolerate re-execution on resume, so side effects must be idempotent.

### D4. MCP for tools, behind our own ToolGateway and permission engine

Integration tools are exposed as MCP servers (spec 2026-07-28, official Python SDK, streamable HTTP on the internal network). Agents reach them only through an in-process ToolGateway that applies our **server-side tool registry** (risk, role, approval rules, schemas), injects tenant scope, redacts results and records evidence.

- *Alternatives:* direct Python function tools (no standard interface for adding third-party servers later). The LLM provider's hosted MCP connector (it would bypass our permission layer and require exposing internal servers publicly).
- *Rationale:* MCP gives a standard, replaceable tool interface. The MCP spec says tool annotations must be treated as untrusted, so risk classification lives in our registry.
- *Risk:* the 2026-07-28 spec is new (stateless core, header-based routing). We pin the SDK version and keep our wrapper thin.

### D5. Evidence-first reasoning with a programmatic grounding validator

Tool results are stored as immutable, hashed evidence. Model claims are typed FACT / INFERENCE / HYPOTHESIS and must cite evidence with verbatim quotes. Code downgrades claims that fail. "Root cause CONFIRMED" can only be set by a successful sandbox reproduction.

- *Alternatives:* relying on prompt instructions such as "only state facts". That isn't verifiable and fails silently.
- *Trade-off:* more structure in outputs means more tokens and occasional valid claims downgraded because of quote mismatches. Acceptable, and tunable (whitespace normalization, fuzzy-match threshold for display only).

### D6. Provider-agnostic LLM interface, with Anthropic Claude as the default implementation

`LLMClient` wraps the official `anthropic` Python SDK. Default model is `claude-opus-5` with adaptive thinking. Per-node model and effort are configurable. Node outputs come through structured outputs (`messages.parse` + Pydantic), and tool inputs are schema-valid via `strict: true` tools. Prompts are cached, refusals handled explicitly, and long generations streamed. `FakeLLMClient` covers tests. `ReplayLLMClient` gives a deterministic demo (clearly labelled, never used for metrics).

- `LLM_MODE=live|replay|fake`. Without an API key the app still runs, and investigations report "LLM not configured" instead of producing fake output.
- Cheaper per-node models are to be decided from Phase 20 evaluation data.

### D7. Separate embedding provider behind an interface

Anthropic has no embeddings endpoint. The default `EmbeddingProvider` is **local `fastembed`** (`BAAI/bge-small-en-v1.5`, 384-dim, ONNX, CPU): no key, no cost, deterministic, offline. The model name is stored per vector, and dimension changes require a re-embed migration.

- *Alternatives:* hosted embedding APIs (another key and bill, network dependency), sentence-transformers (pulls PyTorch, multi-GB images).

### D8. Sandbox: Docker with defence in depth locally, Fargate tasks on AWS

Only `sandbox-runner` talks to the container runtime, through a restricted socket proxy. Each run gets a fresh container: `--network none`, non-root, `cap-drop ALL`, `no-new-privileges`, read-only root filesystem, resource limits, hard timeout, no secrets. gVisor `runsc` is used where the host supports it. On AWS, each run is a separate ECS Fargate task (micro-VM isolation), with no Docker socket.

- *Trade-off:* Docker Desktop on Windows/macOS can't easily use gVisor, so local isolation is weaker than production. This is documented, and acceptable for the local mock environment only.

### D9. Server-Sent Events for live investigation progress

The spec's diagram mentions WebSockets. Progress updates flow server → client only, so SSE is enough, is plain HTTP (auth cookies, proxies, reconnection via `Last-Event-ID`), and needs no extra connection management. User actions stay as REST calls. We'll switch to WebSockets if a bidirectional feature appears.

### D10. Authentication owned by the FastAPI backend

Argon2id passwords. **Server-side sessions:** an opaque random token in an `HttpOnly` cookie, stored hashed in the DB, which also holds the active organization. The browser reaches the API same-origin through a Next.js `/api/*` rewrite, so there's no CORS. CSRF is handled by SameSite cookies plus a required custom header. Tenant isolation is enforced at the router, repository and database levels (composite FKs). RLS is optional and only considered in Phase 21.

- *Alternatives:* JWT access + refresh tokens (more moving parts, harder revocation, no benefit for a single first-party frontend). Auth in Next.js / Auth.js (splits security logic across two runtimes).

### D11. Mock target environment as a separate example app

`examples/shopmock/` is a small Python/FastAPI e-commerce app with a seeded git history, logs, deployments and a database, containing deliberately introduced bugs (coupon checkout first). Support2Fix investigates it through the same adapter interfaces used for real systems.

### D12. Tooling (Python and frontend)

Python 3.13 in containers, managed with `pyproject.toml` + lockfile. Ruff (lint and format), mypy (strict on new code) and pytest. On the frontend: TypeScript strict, ESLint, Prettier, Vitest + Testing Library, Playwright for E2E. OpenAPI-generated TypeScript types. Alembic migrations from Phase 1.

### D13. Simplicity defaults

Explicit choices to keep the project easy to run and reason about. Each can be upgraded later behind an existing interface:

| Area | Simple default | Upgrade path (only if measured need) |
|---|---|---|
| Code host | Local git repo adapter; real GitHub when `GITHUB_TOKEN` (fine-grained PAT) is set | GitHub App |
| Job wakeup / live updates | Polling (≈1 s) | `LISTEN/NOTIFY` |
| Large artifacts | Capped `text` columns in Postgres | S3 object store |
| Tenant isolation | Scoped repositories + composite FKs + tests | Postgres RLS |
| Observability | Structured JSON logs + OTel traces | Prometheus/Grafana stack as an optional Compose profile (Phase 19) |
| Sandbox | Docker with hardening flags | gVisor, Fargate tasks |
| Demo | Runs fully offline with `LLM_MODE=replay` and local adapters | Live LLM + real GitHub |

### D14. Repository

Support2Fix is its **own git repository** rooted at this directory. The enclosing home-directory repository (remote `etl_automation`) must not track it.

## Consequences

- **Positive:** a small operational footprint (one database, one Python image). Strong, code-enforced safety boundaries. Investigations are resumable and auditable. Vendors can be swapped behind interfaces.
- **Negative:** the Postgres queue and SSE have scaling ceilings (acceptable, with swap paths documented). More structure in LLM outputs raises token usage. Local sandbox isolation is weaker than production.
- **Follow-ups:** separate ADRs when we pick the embedding provider (Phase 17), the observability backend details (Phase 19), and when enabling any CRITICAL tool (not planned).

## Risks

| # | Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| R1 | Docker API access = root on host | Med | High | Only sandbox-runner, socket proxy, gVisor, Fargate in production |
| R2 | LLM non-determinism makes the demo flaky | High | Med | Replay mode for demo, fake client in tests, evaluation on live runs |
| R3 | Hallucinated root causes presented confidently | Med | High | Grounding validator, CONFIRMED only via reproduction, visible claim kinds |
| R4 | Prompt injection via tickets, logs or code | High | High | Capability limits, approvals, structured outputs, injection test suite |
| R5 | LLM cost and latency per investigation | Med | Med | Budgets, prompt caching, per-node model tuning from evaluation data |
| R6 | Overfitting to our own seeded bugs | High | Med | Hold-out incidents written independently of prompts, no scenario-specific logic |
| R7 | Scope (25 phases) leads to breadth over depth | High | Med | Thin vertical slice (phases 5–9 on one scenario) before widening |
| R8 | MCP / LangGraph API churn | Med | Low | Pinned versions, thin wrappers, contract tests |
| R9 | Embedding model lock-in (fixed dimensions) | Low | Med | Store model per vector, re-embed migration path |
| R10 | Local dev environment: no Docker installed, Python 3.14 locally vs 3.13 target | High (now) | Med | Install Docker Desktop before Phase 1. Run the backend in containers or pin 3.13 locally. |

## Resolved questions

| Question | Decision |
|---|---|
| LLM provider | Anthropic Claude (`claude-opus-5`) via the official SDK. `ANTHROPIC_API_KEY` in `.env` for live mode. Replay/fake modes work without a key. |
| Embedding provider | Local `fastembed` (bge-small-en-v1.5, 384-dim) |
| GitHub for PR demo | Local git adapter by default. Optional fine-grained PAT (`GITHUB_TOKEN`) on a dedicated test repo for real PRs. |
| Docker | Required from Phase 1 (Docker Desktop, WSL2 backend). Must be installed by the owner, since it needs admin rights and a restart. |
| Git repository | `git init` in the project directory, with a `.gitignore` that excludes secrets and build output |
