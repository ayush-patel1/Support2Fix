"""The `tools` MCP server (Phase 7): tool listing, real adapters wired

through real data (a real temp git repo, the test database itself for
`DATA_SOURCE`), tenant/kind safety, and the service-token boundary.
Requires a reachable TEST_DATABASE_URL — see conftest.py.
"""

import subprocess
import uuid
from pathlib import Path

import httpx2
import pytest
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker

from app.core.ids import uuid7
from app.models.integration import Integration, IntegrationKind, IntegrationProvider
from app.models.organization import Organization
from app.tests.conftest import TEST_DATABASE_URL, mcp_test_session


def _init_git_repo(path: Path) -> None:
    subprocess.run(["git", "init", "-q", str(path)], check=True)
    (path / "README.md").write_text("hello\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(path), "add", "README.md"], check=True)
    subprocess.run(
        [
            "git",
            "-C",
            str(path),
            "-c",
            "user.email=t@t.example",
            "-c",
            "user.name=T",
            "commit",
            "-q",
            "-m",
            "initial",
        ],
        check=True,
    )


async def _seed_org_and_integration(
    engine: AsyncEngine, *, kind: IntegrationKind, config: dict[str, object]
) -> tuple[uuid.UUID, uuid.UUID]:
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as db:
        org = Organization(id=uuid7(), name="MCP Test Org", slug=f"mcp-test-{uuid7()}")
        db.add(org)
        await db.flush()
        integration = Integration(
            id=uuid7(),
            organization_id=org.id,
            kind=kind,
            provider=IntegrationProvider.LOCAL,
            name="test integration",
            config=config,
        )
        db.add(integration)
        await db.commit()
        return org.id, integration.id


async def test_lists_one_tool_per_adapter_method(monkeypatch: pytest.MonkeyPatch):
    async with mcp_test_session(monkeypatch) as (session, _engine):
        tools = await session.list_tools()
        names = {t.name for t in tools.tools}
        assert names == {
            "code.search_code",
            "code.get_file",
            "code.get_commit",
            "code.list_commits",
            "code.create_branch",
            "code.create_pull_request",
            "logs.search_logs",
            "logs.get_event",
            "data.get_schema",
            "data.describe_table",
            "data.run_readonly_query",
            "deploy.get_deployment",
            "deploy.list_releases",
            "deploy.get_service_version",
            "support.get_ticket",
            "support.get_customer",
        }


async def test_code_host_tools_against_real_git_repo(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
    _init_git_repo(tmp_path)
    async with mcp_test_session(monkeypatch) as (session, engine):
        org_id, integration_id = await _seed_org_and_integration(
            engine, kind=IntegrationKind.CODE_HOST, config={"repo_path": str(tmp_path)}
        )

        result = await session.call_tool(
            "code.list_commits",
            {"organization_id": str(org_id), "integration_id": str(integration_id)},
        )
        assert result.is_error is False
        commits = result.structured_content["result"]
        assert len(commits) == 1
        assert commits[0]["message"] == "initial"

        result = await session.call_tool(
            "code.get_file",
            {
                "organization_id": str(org_id),
                "integration_id": str(integration_id),
                "path": "README.md",
            },
        )
        assert result.is_error is False
        assert result.structured_content["content"] == "hello\n"


async def test_data_source_introspects_the_test_database(monkeypatch: pytest.MonkeyPatch):
    async with mcp_test_session(monkeypatch) as (session, engine):
        org_id, integration_id = await _seed_org_and_integration(
            engine, kind=IntegrationKind.DATA_SOURCE, config={"database_url": TEST_DATABASE_URL}
        )

        result = await session.call_tool(
            "data.get_schema",
            {"organization_id": str(org_id), "integration_id": str(integration_id)},
        )
        assert result.is_error is False
        table_names = {t["name"] for t in result.structured_content["result"]}
        assert "organizations" in table_names
        assert "integrations" in table_names


async def test_non_select_query_is_rejected(monkeypatch: pytest.MonkeyPatch):
    async with mcp_test_session(monkeypatch) as (session, engine):
        org_id, integration_id = await _seed_org_and_integration(
            engine, kind=IntegrationKind.DATA_SOURCE, config={"database_url": TEST_DATABASE_URL}
        )

        result = await session.call_tool(
            "data.run_readonly_query",
            {
                "organization_id": str(org_id),
                "integration_id": str(integration_id),
                "sql": "DELETE FROM organizations",
            },
        )
        assert result.is_error is True
        assert "SELECT or WITH" in result.content[0].text


async def test_wrong_kind_integration_is_rejected(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    _init_git_repo(tmp_path)
    async with mcp_test_session(monkeypatch) as (session, engine):
        org_id, integration_id = await _seed_org_and_integration(
            engine, kind=IntegrationKind.CODE_HOST, config={"repo_path": str(tmp_path)}
        )

        result = await session.call_tool(
            "logs.search_logs",
            {"organization_id": str(org_id), "integration_id": str(integration_id), "query": "x"},
        )
        assert result.is_error is True
        assert "expected LOG_SOURCE" in result.content[0].text


async def test_unknown_integration_is_rejected(monkeypatch: pytest.MonkeyPatch):
    async with mcp_test_session(monkeypatch) as (session, _engine):
        result = await session.call_tool(
            "deploy.list_releases",
            {"organization_id": str(uuid.uuid4()), "integration_id": str(uuid.uuid4())},
        )
        assert result.is_error is True
        assert "not found" in result.content[0].text


async def test_service_token_is_required(monkeypatch: pytest.MonkeyPatch):
    from app.core.config import get_settings
    from app.mcp.app import create_app as create_mcp_app

    monkeypatch.setenv("DATABASE_URL", TEST_DATABASE_URL)
    get_settings.cache_clear()
    try:
        app = create_mcp_app()
        async with app.router.lifespan_context(app):
            transport = httpx2.ASGITransport(app=app)
            async with httpx2.AsyncClient(
                transport=transport, base_url="http://127.0.0.1:9999"
            ) as client:
                resp = await client.post("/mcp", json={"jsonrpc": "2.0", "id": 1, "method": "ping"})
            assert resp.status_code == 401
    finally:
        get_settings.cache_clear()


async def test_wrong_service_token_is_rejected(monkeypatch: pytest.MonkeyPatch):
    from app.core.config import get_settings
    from app.mcp.app import create_app as create_mcp_app

    monkeypatch.setenv("DATABASE_URL", TEST_DATABASE_URL)
    get_settings.cache_clear()
    try:
        app = create_mcp_app()
        async with app.router.lifespan_context(app):
            transport = httpx2.ASGITransport(app=app)
            async with httpx2.AsyncClient(
                transport=transport,
                base_url="http://127.0.0.1:9999",
                headers={"Authorization": "Bearer wrong-token"},
            ) as client:
                resp = await client.post("/mcp", json={"jsonrpc": "2.0", "id": 1, "method": "ping"})
            assert resp.status_code == 401
    finally:
        get_settings.cache_clear()
