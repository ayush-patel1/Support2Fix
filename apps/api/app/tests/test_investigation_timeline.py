import uuid
from datetime import UTC, datetime, timedelta

from app.models.investigation import (
    Claim,
    ClaimKind,
    ClaimStatus,
    FixProposal,
    FixProposalStatus,
    InvestigationEvent,
    InvestigationEventType,
    Reproduction,
    ReproductionStatus,
    ValidationRun,
    ValidationStatus,
)
from app.schemas.investigation import (
    ClaimPublic,
    EvidencePublic,
    FixProposalPublic,
    ReproductionPublic,
    ValidationRunPublic,
)
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


def test_claim_public_model_round_trips_reasoning_fields():
    claim = Claim(
        id=uuid.uuid4(),
        organization_id=uuid.uuid4(),
        investigation_id=uuid.uuid4(),
        created_by=uuid.uuid4(),
        statement="The checkout timeout is caused by a missing retry guard.",
        kind=ClaimKind.HYPOTHESIS,
        confidence=0.82,
        status=ClaimStatus.PROPOSED,
        created_at=datetime(2026, 10, 16, tzinfo=UTC),
    )

    public = ClaimPublic.model_validate(claim)

    assert public.kind == ClaimKind.HYPOTHESIS
    assert public.status == ClaimStatus.PROPOSED
    assert public.confidence == 0.82
    assert "retry guard" in public.statement


def test_reproduction_and_validation_public_models_round_trip_state():
    reproduction = Reproduction(
        id=uuid.uuid4(),
        organization_id=uuid.uuid4(),
        investigation_id=uuid.uuid4(),
        spec={"command": ["pytest", "-q"], "timeout_seconds": 30},
        status=ReproductionStatus.RUNNING,
        exit_code=1,
        duration_ms=2500,
        summary="The reproduction is failing with the expected timeout.",
        created_at=datetime(2026, 10, 16, tzinfo=UTC),
        updated_at=datetime(2026, 10, 16, tzinfo=UTC),
    )
    validation = ValidationRun(
        id=uuid.uuid4(),
        organization_id=uuid.uuid4(),
        reproduction_id=reproduction.id,
        status=ValidationStatus.FAILED,
        passed=0,
        failed=2,
        skipped=1,
        repro_fixed=False,
        regression_pass=False,
        logs_ref="logs/validation-1.txt",
        created_at=datetime(2026, 10, 16, tzinfo=UTC),
    )

    reproduction_public = ReproductionPublic.model_validate(reproduction)
    validation_public = ValidationRunPublic.model_validate(validation)

    assert reproduction_public.status == ReproductionStatus.RUNNING
    assert reproduction_public.spec["command"] == ["pytest", "-q"]
    assert validation_public.status == ValidationStatus.FAILED
    assert validation_public.failed == 2
