"""Organization settings + member management: the RBAC matrix and tenant

isolation (security.md §4, §11). Requires a reachable TEST_DATABASE_URL —
see conftest.py.
"""

from httpx import AsyncClient

from app.tests.conftest import CSRF_HEADERS, new_client


async def _register(client: AsyncClient, email: str, org_name: str):
    return await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "correct-horse", "organization_name": org_name},
        headers=CSRF_HEADERS,
    )


async def test_get_current_organization(db_client: AsyncClient):
    await _register(db_client, "admin@acme.example", "Acme")
    resp = await db_client.get("/api/v1/organizations/current")
    assert resp.status_code == 200
    assert resp.json()["name"] == "Acme"


async def test_admin_can_rename_organization(db_client: AsyncClient):
    await _register(db_client, "admin@acme2.example", "Acme Two")
    resp = await db_client.patch(
        "/api/v1/organizations/current", json={"name": "Acme Two Renamed"}, headers=CSRF_HEADERS
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "Acme Two Renamed"


async def test_non_admin_cannot_rename_organization(db_app):
    admin = new_client(db_app)
    await _register(admin, "admin@viewerco.example", "ViewerCo")

    viewer = new_client(db_app)
    await _register(viewer, "viewer@viewerco.example", "Viewer's Own Org")

    add = await admin.post(
        "/api/v1/organizations/current/members",
        json={"email": "viewer@viewerco.example", "role": "VIEWER"},
        headers=CSRF_HEADERS,
    )
    assert add.status_code == 201

    # The viewer's *active* org is still their own (from their own
    # registration) — switch it to ViewerCo, where they were just added.
    me = (await admin.get("/api/v1/organizations/current")).json()
    switch = await viewer.post(
        "/api/v1/auth/switch-org", json={"organization_id": me["id"]}, headers=CSRF_HEADERS
    )
    assert switch.status_code == 200
    assert switch.json()["memberships"][-1]["role"] in ("VIEWER",)

    resp = await viewer.patch(
        "/api/v1/organizations/current", json={"name": "Hijacked"}, headers=CSRF_HEADERS
    )
    assert resp.status_code == 403
    assert resp.json()["title"] == "forbidden"


async def test_add_member_requires_admin(db_app):
    admin = new_client(db_app)
    await _register(admin, "admin@supportco.example", "SupportCo")
    org_id = (await admin.get("/api/v1/organizations/current")).json()["id"]

    support = new_client(db_app)
    await _register(support, "support@own.example", "Own Org")
    await admin.post(
        "/api/v1/organizations/current/members",
        json={"email": "support@own.example", "role": "SUPPORT"},
        headers=CSRF_HEADERS,
    )
    await support.post(
        "/api/v1/auth/switch-org", json={"organization_id": org_id}, headers=CSRF_HEADERS
    )

    resp = await support.post(
        "/api/v1/organizations/current/members",
        json={"email": "nobody@example.com", "role": "VIEWER"},
        headers=CSRF_HEADERS,
    )
    assert resp.status_code == 403


async def test_cannot_demote_or_remove_the_last_admin(db_client: AsyncClient):
    register = await _register(db_client, "solo@lonelyco.example", "LonelyCo")
    user_id = register.json()["id"]

    demote = await db_client.patch(
        f"/api/v1/organizations/current/members/{user_id}",
        json={"role": "VIEWER"},
        headers=CSRF_HEADERS,
    )
    assert demote.status_code == 409
    assert demote.json()["title"] == "conflict"

    remove = await db_client.delete(
        f"/api/v1/organizations/current/members/{user_id}", headers=CSRF_HEADERS
    )
    assert remove.status_code == 409


async def test_members_list_is_isolated_per_organization(db_app):
    org_a_admin = new_client(db_app)
    await _register(org_a_admin, "a-admin@orga.example", "Org A")

    org_b_admin = new_client(db_app)
    await _register(org_b_admin, "b-admin@orgb.example", "Org B")

    members_a = (await org_a_admin.get("/api/v1/organizations/current/members")).json()
    members_b = (await org_b_admin.get("/api/v1/organizations/current/members")).json()

    emails_a = {m["email"] for m in members_a}
    emails_b = {m["email"] for m in members_b}
    assert emails_a == {"a-admin@orga.example"}
    assert emails_b == {"b-admin@orgb.example"}
    assert emails_a.isdisjoint(emails_b)


async def test_add_member_already_a_member_conflicts(db_client: AsyncClient):
    await _register(db_client, "owner@dupco.example", "DupCo")
    add = await db_client.post(
        "/api/v1/organizations/current/members",
        json={"email": "owner@dupco.example", "role": "ENGINEER"},
        headers=CSRF_HEADERS,
    )
    assert add.status_code == 409
    assert add.json()["title"] == "already_exists"


async def test_add_member_unknown_email_not_found(db_client: AsyncClient):
    await _register(db_client, "owner@notfoundco.example", "NotFoundCo")
    resp = await db_client.post(
        "/api/v1/organizations/current/members",
        json={"email": "nobody-registered@example.com", "role": "VIEWER"},
        headers=CSRF_HEADERS,
    )
    assert resp.status_code == 404


async def test_add_update_role_then_remove_a_real_member(db_app):
    admin = new_client(db_app)
    await _register(admin, "owner@fullflow.example", "FullFlow Co")

    other = new_client(db_app)
    await _register(other, "member@fullflow.example", "Member's Own Org")

    add = await admin.post(
        "/api/v1/organizations/current/members",
        json={"email": "member@fullflow.example", "role": "VIEWER"},
        headers=CSRF_HEADERS,
    )
    assert add.status_code == 201
    user_id = add.json()["user_id"]

    members = (await admin.get("/api/v1/organizations/current/members")).json()
    assert {"member@fullflow.example"} <= {m["email"] for m in members}

    promote = await admin.patch(
        f"/api/v1/organizations/current/members/{user_id}",
        json={"role": "SUPPORT"},
        headers=CSRF_HEADERS,
    )
    assert promote.status_code == 200
    assert promote.json()["role"] == "SUPPORT"

    remove = await admin.delete(
        f"/api/v1/organizations/current/members/{user_id}", headers=CSRF_HEADERS
    )
    assert remove.status_code == 204

    members_after = (await admin.get("/api/v1/organizations/current/members")).json()
    assert "member@fullflow.example" not in {m["email"] for m in members_after}
