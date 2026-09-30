"""Authentication flows: register, login, /me, logout, org switching, and

the CSRF header defense. Requires a reachable TEST_DATABASE_URL — see
conftest.py's `db_app` fixture, which skips (not fails) if it can't
connect.
"""

from httpx import AsyncClient

from app.tests.conftest import CSRF_HEADERS, new_client


async def _register(
    client: AsyncClient, email: str, org_name: str, password: str = "correct-horse"
):
    return await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "organization_name": org_name},
        headers=CSRF_HEADERS,
    )


async def test_register_creates_user_and_admin_session(db_client: AsyncClient):
    resp = await _register(db_client, "alice@example.com", "Alice Co")
    assert resp.status_code == 201
    body = resp.json()
    assert body["email"] == "alice@example.com"
    assert "s2f_session" in resp.cookies

    me = await db_client.get("/api/v1/auth/me")
    assert me.status_code == 200
    me_body = me.json()
    assert me_body["user"]["email"] == "alice@example.com"
    assert len(me_body["memberships"]) == 1
    assert me_body["memberships"][0]["role"] == "ADMIN"
    assert me_body["active_organization_id"] == me_body["memberships"][0]["organization_id"]


async def test_register_duplicate_email_conflicts(db_client: AsyncClient):
    await _register(db_client, "bob@example.com", "Bob Co")
    resp = await _register(db_client, "bob@example.com", "Another Co")
    assert resp.status_code == 409
    assert resp.json()["title"] == "already_exists"


async def test_login_wrong_password_and_unknown_user_match(db_client: AsyncClient, db_app):
    await _register(db_client, "carol@example.com", "Carol Co", password="right-password")

    wrong_pw = await new_client(db_app).post(
        "/api/v1/auth/login",
        json={"email": "carol@example.com", "password": "wrong-password"},
        headers=CSRF_HEADERS,
    )
    unknown_user = await new_client(db_app).post(
        "/api/v1/auth/login",
        json={"email": "nobody@example.com", "password": "whatever"},
        headers=CSRF_HEADERS,
    )

    assert wrong_pw.status_code == 401
    assert unknown_user.status_code == 401
    # Same error for both, so a caller can't use this endpoint to enumerate
    # registered emails — see security.md §10.
    assert wrong_pw.json()["detail"] == unknown_user.json()["detail"]


async def test_me_without_session_is_401(db_client: AsyncClient):
    resp = await db_client.get("/api/v1/auth/me")
    assert resp.status_code == 401
    assert resp.json()["title"] == "authentication_required"


async def test_logout_invalidates_the_session(db_client: AsyncClient):
    await _register(db_client, "dave@example.com", "Dave Co")
    assert (await db_client.get("/api/v1/auth/me")).status_code == 200

    logout = await db_client.post("/api/v1/auth/logout", headers=CSRF_HEADERS)
    assert logout.status_code == 204

    assert (await db_client.get("/api/v1/auth/me")).status_code == 401


async def test_csrf_header_required_on_mutating_requests(db_client: AsyncClient):
    resp = await db_client.post(
        "/api/v1/auth/register",
        json={
            "email": "erin@example.com",
            "password": "correct-horse",
            "organization_name": "Erin Co",
        },
        # deliberately no CSRF header
    )
    assert resp.status_code == 403
    assert resp.json()["title"] == "csrf_header_missing"


async def test_switch_org_requires_membership(db_app):
    user1 = new_client(db_app)
    user2 = new_client(db_app)

    await _register(user1, "frank@example.com", "Frank Co")
    org2_resp = await _register(user2, "grace@example.com", "Grace Co")
    org2_id = (await user2.get("/api/v1/auth/me")).json()["active_organization_id"]
    assert org2_resp.status_code == 201

    resp = await user1.post(
        "/api/v1/auth/switch-org", json={"organization_id": org2_id}, headers=CSRF_HEADERS
    )
    assert resp.status_code == 403
    assert resp.json()["title"] == "forbidden"
