import pytest
from httpx import ASGITransport, AsyncClient

from app.main import create_app


@pytest.fixture
async def client():
    """An ASGI test client. No real Postgres is required: the /health

    liveness check does not touch the database, and /api/v1/health degrades
    gracefully (status 503, database: "unreachable") when it can't connect
    instead of raising — see test_health.py.
    """
    app = create_app()
    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac
