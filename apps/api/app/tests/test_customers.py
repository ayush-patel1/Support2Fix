"""Customer -> Environment -> Service -> {Repository, Deployment}: CRUD,

hierarchy validation, RBAC and tenant isolation. Requires a reachable
TEST_DATABASE_URL — see conftest.py.
"""

from httpx import AsyncClient

from app.tests.conftest import CSRF_HEADERS, new_client


async def _register(client: AsyncClient, email: str, org_name: str):
    return await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "correct-horse", "organization_name": org_name},
        headers=CSRF_HEADERS,
    )


async def test_create_and_get_customer(db_client: AsyncClient):
    await _register(db_client, "admin@custco.example", "CustCo")
    create = await db_client.post(
        "/api/v1/customers",
        json={"name": "Acme Commerce", "tier": "ENTERPRISE"},
        headers=CSRF_HEADERS,
    )
    assert create.status_code == 201
    customer_id = create.json()["id"]
    assert create.json()["tier"] == "ENTERPRISE"

    get = await db_client.get(f"/api/v1/customers/{customer_id}")
    assert get.status_code == 200
    assert get.json()["name"] == "Acme Commerce"


async def test_viewer_cannot_create_customer(db_app):
    admin = new_client(db_app)
    await _register(admin, "admin@viewerco2.example", "ViewerCo2")
    org_id = (await admin.get("/api/v1/organizations/current")).json()["id"]

    viewer = new_client(db_app)
    await _register(viewer, "viewer@own2.example", "Viewer Own Org")
    await admin.post(
        "/api/v1/organizations/current/members",
        json={"email": "viewer@own2.example", "role": "VIEWER"},
        headers=CSRF_HEADERS,
    )
    await viewer.post(
        "/api/v1/auth/switch-org", json={"organization_id": org_id}, headers=CSRF_HEADERS
    )

    resp = await viewer.post("/api/v1/customers", json={"name": "Nope Inc"}, headers=CSRF_HEADERS)
    assert resp.status_code == 403


async def test_create_environment_requires_existing_customer(db_client: AsyncClient):
    await _register(db_client, "admin@envco.example", "EnvCo")
    fake_id = "00000000-0000-7000-8000-000000000000"
    resp = await db_client.post(
        f"/api/v1/customers/{fake_id}/environments",
        json={"name": "production"},
        headers=CSRF_HEADERS,
    )
    assert resp.status_code == 404


async def test_environment_overview_returns_full_chain(db_client: AsyncClient):
    await _register(db_client, "admin@chainco.example", "ChainCo")
    customer_id = (
        await db_client.post(
            "/api/v1/customers", json={"name": "Chain Customer"}, headers=CSRF_HEADERS
        )
    ).json()["id"]
    env_id = (
        await db_client.post(
            f"/api/v1/customers/{customer_id}/environments",
            json={"name": "production"},
            headers=CSRF_HEADERS,
        )
    ).json()["id"]
    service_id = (
        await db_client.post(
            f"/api/v1/customers/{customer_id}/environments/{env_id}/services",
            json={"name": "checkout", "language": "TypeScript"},
            headers=CSRF_HEADERS,
        )
    ).json()["id"]
    await db_client.post(
        f"/api/v1/services/{service_id}/repositories",
        json={"full_name": "acme/checkout", "provider": "LOCAL"},
        headers=CSRF_HEADERS,
    )
    await db_client.post(
        f"/api/v1/services/{service_id}/deployments",
        json={"version": "v2.8.1", "commit_sha": "8a92c1f", "status": "SUCCESS"},
        headers=CSRF_HEADERS,
    )

    overview = await db_client.get(f"/api/v1/customers/{customer_id}/environments/{env_id}")
    assert overview.status_code == 200
    body = overview.json()
    assert body["environment"]["name"] == "production"
    assert len(body["services"]) == 1
    service = body["services"][0]
    assert service["service"]["name"] == "checkout"
    assert len(service["repositories"]) == 1
    assert service["repositories"][0]["full_name"] == "acme/checkout"
    assert len(service["deployments"]) == 1
    assert service["deployments"][0]["version"] == "v2.8.1"


async def test_service_creation_rejects_environment_from_wrong_customer(db_client: AsyncClient):
    await _register(db_client, "admin@mismatch.example", "MismatchCo")
    customer_a = (
        await db_client.post("/api/v1/customers", json={"name": "Customer A"}, headers=CSRF_HEADERS)
    ).json()["id"]
    customer_b = (
        await db_client.post("/api/v1/customers", json={"name": "Customer B"}, headers=CSRF_HEADERS)
    ).json()["id"]
    env_a = (
        await db_client.post(
            f"/api/v1/customers/{customer_a}/environments",
            json={"name": "production"},
            headers=CSRF_HEADERS,
        )
    ).json()["id"]

    # env_a belongs to customer_a, not customer_b — claiming it under
    # customer_b's URL must 404, not silently succeed.
    resp = await db_client.post(
        f"/api/v1/customers/{customer_b}/environments/{env_a}/services",
        json={"name": "checkout"},
        headers=CSRF_HEADERS,
    )
    assert resp.status_code == 404


async def test_customers_isolated_per_organization(db_app):
    org_a = new_client(db_app)
    await _register(org_a, "admin@orga3.example", "Org A3")
    await org_a.post("/api/v1/customers", json={"name": "Org A Customer"}, headers=CSRF_HEADERS)

    org_b = new_client(db_app)
    await _register(org_b, "admin@orgb3.example", "Org B3")
    await org_b.post("/api/v1/customers", json={"name": "Org B Customer"}, headers=CSRF_HEADERS)

    list_a = (await org_a.get("/api/v1/customers")).json()
    list_b = (await org_b.get("/api/v1/customers")).json()
    names_a = {c["name"] for c in list_a}
    names_b = {c["name"] for c in list_b}
    assert names_a == {"Org A Customer"}
    assert names_b == {"Org B Customer"}
