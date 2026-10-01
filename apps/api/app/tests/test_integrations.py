"""Integration CRUD, config validation, RBAC, tenant isolation, and

test-connection against real local adapters (a real temp git repo, a real
JSONL log file, a real deployments.json) — not mocks. Requires a reachable
TEST_DATABASE_URL — see conftest.py.
"""

import json
import subprocess
from pathlib import Path

import pytest
from httpx import AsyncClient

from app.tests.conftest import CSRF_HEADERS, new_client


async def _register(client: AsyncClient, email: str, org_name: str):
    return await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "correct-horse", "organization_name": org_name},
        headers=CSRF_HEADERS,
    )


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


async def test_create_list_get_update_delete_integration(db_client: AsyncClient, tmp_path: Path):
    await _register(db_client, "admin@introco.example", "IntroCo")
    _init_git_repo(tmp_path)

    create = await db_client.post(
        "/api/v1/integrations",
        json={
            "kind": "CODE_HOST",
            "provider": "LOCAL",
            "name": "Primary repo",
            "config": {"repo_path": str(tmp_path)},
        },
        headers=CSRF_HEADERS,
    )
    assert create.status_code == 201
    integration_id = create.json()["id"]
    assert "secret_ref" not in create.json()

    listed = await db_client.get("/api/v1/integrations")
    assert listed.status_code == 200
    assert len(listed.json()) == 1

    filtered = await db_client.get("/api/v1/integrations", params={"kind": "LOG_SOURCE"})
    assert filtered.json() == []

    got = await db_client.get(f"/api/v1/integrations/{integration_id}")
    assert got.status_code == 200
    assert got.json()["name"] == "Primary repo"

    updated = await db_client.patch(
        f"/api/v1/integrations/{integration_id}",
        json={"name": "Renamed repo"},
        headers=CSRF_HEADERS,
    )
    assert updated.status_code == 200
    assert updated.json()["name"] == "Renamed repo"

    deleted = await db_client.delete(f"/api/v1/integrations/{integration_id}", headers=CSRF_HEADERS)
    assert deleted.status_code == 204
    assert (await db_client.get(f"/api/v1/integrations/{integration_id}")).status_code == 404


async def test_create_rejects_invalid_config(db_client: AsyncClient):
    await _register(db_client, "admin@badconfco.example", "BadConfCo")

    resp = await db_client.post(
        "/api/v1/integrations",
        json={"kind": "CODE_HOST", "provider": "LOCAL", "name": "No path", "config": {}},
        headers=CSRF_HEADERS,
    )
    assert resp.status_code == 400
    assert resp.json()["title"] == "invalid_config"


async def test_create_rejects_nonexistent_repo_path(db_client: AsyncClient, tmp_path: Path):
    await _register(db_client, "admin@ghostrepoco.example", "GhostRepoCo")

    resp = await db_client.post(
        "/api/v1/integrations",
        json={
            "kind": "CODE_HOST",
            "provider": "LOCAL",
            "name": "Ghost repo",
            "config": {"repo_path": str(tmp_path / "does-not-exist")},
        },
        headers=CSRF_HEADERS,
    )
    assert resp.status_code == 400
    assert resp.json()["title"] == "invalid_config"


async def test_viewer_cannot_create_integration(db_app):
    admin = new_client(db_app)
    await _register(admin, "admin@viewerintco.example", "ViewerIntCo")

    viewer = new_client(db_app)
    await _register(viewer, "viewer@ownintco.example", "Viewer Own Int Org")
    org_id = (await admin.get("/api/v1/organizations/current")).json()["id"]
    await admin.post(
        "/api/v1/organizations/current/members",
        json={"email": "viewer@ownintco.example", "role": "VIEWER"},
        headers=CSRF_HEADERS,
    )
    await viewer.post(
        "/api/v1/auth/switch-org", json={"organization_id": org_id}, headers=CSRF_HEADERS
    )

    resp = await viewer.post(
        "/api/v1/integrations",
        json={"kind": "LOG_SOURCE", "provider": "LOCAL", "name": "x", "config": {"log_path": "x"}},
        headers=CSRF_HEADERS,
    )
    assert resp.status_code == 403


async def test_engineer_cannot_manage_integrations(db_app):
    admin = new_client(db_app)
    await _register(admin, "admin@engintco.example", "EngIntCo")

    engineer = new_client(db_app)
    await _register(engineer, "eng@ownengintco.example", "Eng Own Int Org")
    org_id = (await admin.get("/api/v1/organizations/current")).json()["id"]
    await admin.post(
        "/api/v1/organizations/current/members",
        json={"email": "eng@ownengintco.example", "role": "ENGINEER"},
        headers=CSRF_HEADERS,
    )
    await engineer.post(
        "/api/v1/auth/switch-org", json={"organization_id": org_id}, headers=CSRF_HEADERS
    )

    resp = await engineer.get("/api/v1/integrations")
    assert resp.status_code == 403


async def test_integration_is_tenant_isolated(db_app, tmp_path: Path):
    log_file = tmp_path / "application.jsonl"
    log_file.write_text("", encoding="utf-8")

    org_a = new_client(db_app)
    await _register(org_a, "admin@tenantaco.example", "TenantA Co")
    create = await org_a.post(
        "/api/v1/integrations",
        json={
            "kind": "LOG_SOURCE",
            "provider": "LOCAL",
            "name": "A's logs",
            "config": {"log_path": str(log_file)},
        },
        headers=CSRF_HEADERS,
    )
    integration_id = create.json()["id"]

    org_b = new_client(db_app)
    await _register(org_b, "admin@tenantbco.example", "TenantB Co")
    resp = await org_b.get(f"/api/v1/integrations/{integration_id}")
    assert resp.status_code == 404


@pytest.mark.parametrize(
    ("kind", "config_key", "make_target"),
    [
        ("CODE_HOST", "repo_path", "repo"),
        ("LOG_SOURCE", "log_path", "log"),
        ("DEPLOYMENT_SOURCE", "deployments_path", "deployments"),
    ],
)
async def test_test_connection_succeeds_against_real_local_target(
    db_client: AsyncClient, tmp_path: Path, kind: str, config_key: str, make_target: str
):
    await _register(db_client, f"admin@{make_target}testco.example", f"{make_target} TestCo")

    if make_target == "repo":
        _init_git_repo(tmp_path)
        target = str(tmp_path)
    elif make_target == "log":
        log_file = tmp_path / "application.jsonl"
        log_file.write_text(
            json.dumps(
                {
                    "timestamp": "2026-09-30T14:21:04+00:00",
                    "level": "INFO",
                    "service": "x",
                    "message": "hello",
                }
            )
            + "\n",
            encoding="utf-8",
        )
        target = str(log_file)
    else:
        deployments_file = tmp_path / "deployments.json"
        deployments_file.write_text(
            json.dumps(
                [
                    {
                        "service": "x",
                        "version": "v1",
                        "commit_sha": "abc123",
                        "deployed_at": "2026-09-30T14:21:04+00:00",
                        "status": "SUCCESS",
                    }
                ]
            ),
            encoding="utf-8",
        )
        target = str(deployments_file)

    create = await db_client.post(
        "/api/v1/integrations",
        json={
            "kind": kind,
            "provider": "LOCAL",
            "name": "Target",
            "config": {config_key: target},
        },
        headers=CSRF_HEADERS,
    )
    assert create.status_code == 201
    integration_id = create.json()["id"]

    result = await db_client.post(
        f"/api/v1/integrations/{integration_id}/test", headers=CSRF_HEADERS
    )
    assert result.status_code == 200
    body = result.json()
    assert body["ok"] is True, body["detail"]
