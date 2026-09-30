async def test_liveness_ok(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


async def test_readiness_reports_db_status(client):
    """No Postgres is running in the unit-test environment, so this asserts

    the *shape* and the graceful-degradation behavior (503, not a crash) —
    see system-design.md §9 (failure handling) and ADR-001.
    """
    resp = await client.get("/api/v1/health")
    body = resp.json()
    assert set(body.keys()) == {"status", "database"}
    assert resp.status_code in (200, 503)
    if resp.status_code == 503:
        assert body == {"status": "degraded", "database": "unreachable"}
    else:
        assert body == {"status": "ok", "database": "ok"}
