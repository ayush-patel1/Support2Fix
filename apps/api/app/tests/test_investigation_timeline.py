import uuid
from datetime import UTC, datetime, timedelta

from app.models.investigation import InvestigationEvent, InvestigationEventType
from app.schemas.investigation import EvidencePublic
from app.services.investigations import build_investigation_timeline


def test_timeline_combines_events_and_evidence_in_time_order():
    start = datetime(2026, 10, 16, tzinfo=UTC)
    event_id = uuid.uuid4()
    evidence_id = uuid.uuid4()
    events = [
        InvestigationEvent(
            id=event_id,
            organization_id=uuid.uuid4(),
            investigation_id=uuid.uuid4(),
            type=InvestigationEventType.TOOL_COMPLETED,
            message="Collected logs.",
            details={"tool_name": "logs.search_logs"},
            created_at=start + timedelta(seconds=2),
        )
    ]
    evidence = [
        EvidencePublic(
            id=evidence_id,
            kind="log",
            source_ref="log:checkout:1",
            content={"message": "TimeoutError"},
            content_sha256="a" * 64,
            observed_at=start + timedelta(seconds=1),
            tool_name="logs.search_logs",
        )
    ]

    timeline = build_investigation_timeline(events, evidence)

    assert [item.kind for item in timeline] == ["EVIDENCE", "EVENT"]
    assert timeline[0].evidence_id == evidence_id
    assert timeline[0].details["source_ref"] == "log:checkout:1"
    assert timeline[1].title == "Collected logs."
