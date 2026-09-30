# Development image for the api / worker / tools / sandbox-runner entrypoints
# (see docs/architecture/system-design.md §2 — one image, several commands).
# A hardened, multi-stage production build is introduced in Phase 23.
FROM python:3.13-slim

WORKDIR /app

COPY pyproject.toml ./
COPY app ./app
COPY alembic ./alembic
COPY alembic.ini ./

RUN pip install --no-cache-dir -e ".[dev]"

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
