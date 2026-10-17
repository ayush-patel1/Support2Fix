import uuid

import pytest

from app.agents.diagnosis import Diagnosis
from app.core.config import Settings
from app.worker.investigations import _configured_diagnosis_client, _ground_diagnosis


def test_live_diagnosis_requires_explicit_external_data_consent():
    client, reason = _configured_diagnosis_client(
        Settings(llm_mode="live", gemini_api_key="test-key")
    )

    assert client is None
    assert reason is not None
    assert "LLM_ALLOW_EXTERNAL_DATA=true" in reason


def test_live_diagnosis_requires_provider_key_after_consent():
    client, reason = _configured_diagnosis_client(
        Settings(llm_mode="live", llm_allow_external_data=True)
    )

    assert client is None
    assert reason == "AI diagnosis was skipped: GEMINI_API_KEY is not configured."


def test_fake_mode_does_not_create_external_provider_client():
    client, reason = _configured_diagnosis_client(Settings(llm_mode="fake"))

    assert client is None
    assert reason is None


def test_grounded_diagnosis_requires_known_log_and_matching_code_citations():
    log_id = uuid.uuid4()
    code_id = uuid.uuid4()
    diagnosis = Diagnosis(
        summary="A retry exhaustion handler appears to be the failing path.",
        signature="PaymentRetryExhausted",
        path="app/payment.py",
        line_number=42,
        confidence=0.72,
        evidence_ids=[log_id, code_id],
    )

    candidate = _ground_diagnosis(
        diagnosis,
        log_evidence_id=log_id,
        code_evidence_ids=[code_id],
        log_entries=[{"message": "checkout failed: PaymentRetryExhausted"}],
        code_matches=[
            {
                "path": "app/payment.py",
                "line_number": 42,
                "line": "raise PaymentRetryExhausted('retry limit')",
            }
        ],
    )

    assert candidate["classification"] == "HYPOTHESIS"
    assert candidate["evidence_ids"] == [str(log_id), str(code_id)]
    assert "not a confirmed root cause" in candidate["summary"]


def test_grounded_diagnosis_rejects_fabricated_evidence_id():
    log_id = uuid.uuid4()
    code_id = uuid.uuid4()
    diagnosis = Diagnosis(
        summary="Potential failure path.",
        signature="PAY-1042",
        path="payments/handler.py",
        line_number=7,
        confidence=0.5,
        evidence_ids=[log_id, uuid.uuid4()],
    )

    with pytest.raises(ValueError, match="not collected"):
        _ground_diagnosis(
            diagnosis,
            log_evidence_id=log_id,
            code_evidence_ids=[code_id],
            log_entries=[{"message": "PAY-1042"}],
            code_matches=[
                {"path": "payments/handler.py", "line_number": 7, "line": "raise PAY-1042"}
            ],
        )


def test_grounded_diagnosis_rejects_unverified_source_location():
    log_id = uuid.uuid4()
    code_id = uuid.uuid4()
    diagnosis = Diagnosis(
        summary="Potential failure path.",
        signature="PAY-1042",
        path="payments/handler.py",
        line_number=8,
        confidence=0.5,
        evidence_ids=[log_id, code_id],
    )

    with pytest.raises(ValueError, match="source location"):
        _ground_diagnosis(
            diagnosis,
            log_evidence_id=log_id,
            code_evidence_ids=[code_id],
            log_entries=[{"message": "PAY-1042"}],
            code_matches=[
                {"path": "payments/handler.py", "line_number": 7, "line": "raise PAY-1042"}
            ],
        )
