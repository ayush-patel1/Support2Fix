"""Tickets: CRUD, filtering/search, the status state machine, and the

timeline. Requires a reachable TEST_DATABASE_URL — see conftest.py.
"""

from httpx import AsyncClient

from app.tests.conftest import CSRF_HEADERS, new_client


async def _register(client: AsyncClient, email: str, org_name: str):
    return await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "correct-horse", "organization_name": org_name},
        headers=CSRF_HEADERS,
    )


async def _create_customer(client: AsyncClient, name: str = "Acme Commerce") -> str:
    resp = await client.post("/api/v1/customers", json={"name": name}, headers=CSRF_HEADERS)
    result: str = resp.json()["id"]
    return result


async def test_create_and_get_ticket(db_client: AsyncClient):
    await _register(db_client, "admin@ticketco.example", "TicketCo")
    customer_id = await _create_customer(db_client)

    create = await db_client.post(
        "/api/v1/tickets",
        json={
            "customer_id": customer_id,
            "title": "Checkout freezes after SAVE100",
            "description": "Coupon zeroes the order total and the retry loop never resolves.",
            "priority": "CRITICAL",
        },
        headers=CSRF_HEADERS,
    )
    assert create.status_code == 201
    body = create.json()
    assert body["status"] == "OPEN"
    assert body["priority"] == "CRITICAL"

    get = await db_client.get(f"/api/v1/tickets/{body['id']}")
    assert get.status_code == 200
    assert get.json()["title"] == "Checkout freezes after SAVE100"


async def test_create_ticket_requires_existing_customer(db_client: AsyncClient):
    await _register(db_client, "admin@noco.example", "NoCo")
    fake_id = "00000000-0000-7000-8000-000000000000"
    resp = await db_client.post(
        "/api/v1/tickets",
        json={"customer_id": fake_id, "title": "x"},
        headers=CSRF_HEADERS,
    )
    assert resp.status_code == 404


async def test_viewer_cannot_create_ticket(db_app):
    admin = new_client(db_app)
    await _register(admin, "admin@viewerticket.example", "ViewerTicketCo")
    org_id = (await admin.get("/api/v1/organizations/current")).json()["id"]
    customer_id = await _create_customer(admin)

    viewer = new_client(db_app)
    await _register(viewer, "viewer@ownticket.example", "Viewer Own Ticket Org")
    await admin.post(
        "/api/v1/organizations/current/members",
        json={"email": "viewer@ownticket.example", "role": "VIEWER"},
        headers=CSRF_HEADERS,
    )
    await viewer.post(
        "/api/v1/auth/switch-org", json={"organization_id": org_id}, headers=CSRF_HEADERS
    )

    resp = await viewer.post(
        "/api/v1/tickets",
        json={"customer_id": customer_id, "title": "Should be forbidden"},
        headers=CSRF_HEADERS,
    )
    assert resp.status_code == 403


async def test_list_tickets_with_filters_and_search(db_client: AsyncClient):
    await _register(db_client, "admin@filterco.example", "FilterCo")
    customer_id = await _create_customer(db_client)

    await db_client.post(
        "/api/v1/tickets",
        json={"customer_id": customer_id, "title": "Coupon bug", "priority": "HIGH"},
        headers=CSRF_HEADERS,
    )
    await db_client.post(
        "/api/v1/tickets",
        json={"customer_id": customer_id, "title": "Login timeout", "priority": "LOW"},
        headers=CSRF_HEADERS,
    )

    by_priority = await db_client.get("/api/v1/tickets", params={"priority": "HIGH"})
    titles = {t["title"] for t in by_priority.json()["items"]}
    assert titles == {"Coupon bug"}

    by_search = await db_client.get("/api/v1/tickets", params={"search": "login"})
    titles = {t["title"] for t in by_search.json()["items"]}
    assert titles == {"Login timeout"}

    by_status = await db_client.get("/api/v1/tickets", params={"status": "RESOLVED"})
    assert by_status.json()["items"] == []


async def test_valid_status_transition_succeeds(db_client: AsyncClient):
    await _register(db_client, "admin@transitionco.example", "TransitionCo")
    customer_id = await _create_customer(db_client)
    ticket_id = (
        await db_client.post(
            "/api/v1/tickets",
            json={"customer_id": customer_id, "title": "x"},
            headers=CSRF_HEADERS,
        )
    ).json()["id"]

    resp = await db_client.post(
        f"/api/v1/tickets/{ticket_id}/status",
        json={"status": "INVESTIGATING"},
        headers=CSRF_HEADERS,
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "INVESTIGATING"


async def test_invalid_status_transition_is_rejected(db_client: AsyncClient):
    await _register(db_client, "admin@illegalco.example", "IllegalCo")
    customer_id = await _create_customer(db_client)
    ticket_id = (
        await db_client.post(
            "/api/v1/tickets",
            json={"customer_id": customer_id, "title": "x"},
            headers=CSRF_HEADERS,
        )
    ).json()["id"]

    # OPEN -> RESOLVED directly skips the whole investigation — not allowed.
    resp = await db_client.post(
        f"/api/v1/tickets/{ticket_id}/status", json={"status": "RESOLVED"}, headers=CSRF_HEADERS
    )
    assert resp.status_code == 409
    assert resp.json()["title"] == "conflict"


async def test_full_lifecycle_and_resolved_is_terminal(db_client: AsyncClient):
    await _register(db_client, "admin@lifecycleco.example", "LifecycleCo")
    customer_id = await _create_customer(db_client)
    ticket_id = (
        await db_client.post(
            "/api/v1/tickets",
            json={"customer_id": customer_id, "title": "x"},
            headers=CSRF_HEADERS,
        )
    ).json()["id"]

    path = [
        "INVESTIGATING",
        "ROOT_CAUSE_FOUND",
        "FIX_PROPOSED",
        "VALIDATING",
        "RESOLVED",
    ]
    for status in path:
        resp = await db_client.post(
            f"/api/v1/tickets/{ticket_id}/status", json={"status": status}, headers=CSRF_HEADERS
        )
        assert resp.status_code == 200, f"transition to {status} failed: {resp.json()}"
        assert resp.json()["status"] == status

    # RESOLVED is terminal — no further transition is legal.
    resp = await db_client.post(
        f"/api/v1/tickets/{ticket_id}/status",
        json={"status": "INVESTIGATING"},
        headers=CSRF_HEADERS,
    )
    assert resp.status_code == 409


async def test_timeline_records_creation_status_change_and_comment(db_client: AsyncClient):
    await _register(db_client, "admin@timelineco.example", "TimelineCo")
    customer_id = await _create_customer(db_client)
    ticket_id = (
        await db_client.post(
            "/api/v1/tickets",
            json={"customer_id": customer_id, "title": "x"},
            headers=CSRF_HEADERS,
        )
    ).json()["id"]

    await db_client.post(
        f"/api/v1/tickets/{ticket_id}/status",
        json={"status": "INVESTIGATING"},
        headers=CSRF_HEADERS,
    )
    await db_client.post(
        f"/api/v1/tickets/{ticket_id}/events",
        json={"comment": "Reproduced locally with a zero-dollar cart."},
        headers=CSRF_HEADERS,
    )

    events = (await db_client.get(f"/api/v1/tickets/{ticket_id}/events")).json()
    types = [e["type"] for e in events]
    assert types == ["CREATED", "STATUS_CHANGED", "COMMENT"]
    assert events[1]["payload"] == {"from": "OPEN", "to": "INVESTIGATING"}
    assert events[2]["payload"]["comment"] == "Reproduced locally with a zero-dollar cart."


async def test_tickets_isolated_per_organization(db_app):
    org_a = new_client(db_app)
    await _register(org_a, "admin@ticketsorga.example", "TicketsOrgA")
    customer_a = await _create_customer(org_a, "Customer A")
    await org_a.post(
        "/api/v1/tickets",
        json={"customer_id": customer_a, "title": "Org A ticket"},
        headers=CSRF_HEADERS,
    )

    org_b = new_client(db_app)
    await _register(org_b, "admin@ticketsorgb.example", "TicketsOrgB")
    customer_b = await _create_customer(org_b, "Customer B")
    await org_b.post(
        "/api/v1/tickets",
        json={"customer_id": customer_b, "title": "Org B ticket"},
        headers=CSRF_HEADERS,
    )

    titles_a = {t["title"] for t in (await org_a.get("/api/v1/tickets")).json()["items"]}
    titles_b = {t["title"] for t in (await org_b.get("/api/v1/tickets")).json()["items"]}
    assert titles_a == {"Org A ticket"}
    assert titles_b == {"Org B ticket"}
