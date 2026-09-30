# Support2Fix

Support2Fix is an AI platform that turns a customer support issue into an evidence-backed engineering investigation. The flow runs: root cause → reproduction → validated fix → human-approved pull request → customer response.

> **Status: Phase 0 (architecture).** No application code yet. The full README (setup, running, testing, demo) arrives with Phase 1 onward.

## Architecture documents

- [System design](docs/architecture/system-design.md): components, data flow, data model, API boundaries, integrations, failure handling, deployment
- [Agent architecture](docs/architecture/agent-architecture.md): LangGraph workflow, MCP ToolGateway, evidence and grounding, LLM layer
- [Security model](docs/architecture/security.md): threat model, RBAC, tool permissions, prompt-injection defenses, sandbox isolation
- [ADR-001: Initial architecture](docs/decisions/001-architecture.md): decisions, alternatives, risks, open questions

## Planned stack

Next.js · React · TypeScript · Tailwind CSS · FastAPI · Pydantic · SQLAlchemy · LangGraph · MCP · PostgreSQL + pgvector · Docker Compose · GitHub Actions · AWS-compatible deployment
