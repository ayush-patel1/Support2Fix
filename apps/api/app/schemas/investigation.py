import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.models.investigation import (
    ApprovalDecision,
    ClaimKind,
    ClaimStatus,
    FixProposalStatus,
    InvestigationEventType,
    InvestigationStatus,
    ReproductionStatus,
    ValidationStatus,
)


class InvestigationPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    ticket_id: uuid.UUID
    status: InvestigationStatus
    summary: str | None
    candidate: dict[str, Any] | None
    evidence_gaps: list[str]
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None


class EvidencePublic(BaseModel):
    id: uuid.UUID
    kind: str
    source_ref: str | None
    content: Any
    content_sha256: str
    observed_at: datetime
    tool_name: str


class InvestigationTimelineItem(BaseModel):
    id: uuid.UUID
    kind: Literal["EVENT", "EVIDENCE"]
    occurred_at: datetime
    title: str
    details: dict[str, Any]
    evidence_id: uuid.UUID | None = None


class ClaimPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    investigation_id: uuid.UUID
    statement: str
    kind: ClaimKind
    confidence: float
    status: ClaimStatus
    created_at: datetime


class InvestigationClaimCreate(BaseModel):
    statement: str
    kind: ClaimKind
    confidence: float = 0.0
    evidence_ids: list[uuid.UUID] = Field(default_factory=list)
    evidence_quotes: dict[str, str] = Field(default_factory=dict)


class ReproductionPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    investigation_id: uuid.UUID
    status: ReproductionStatus
    spec: dict[str, Any]
    logs_ref: str | None
    exit_code: int | None
    duration_ms: int | None
    summary: str | None
    created_at: datetime
    updated_at: datetime


class ValidationRunPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    reproduction_id: uuid.UUID | None = None
    fix_proposal_id: uuid.UUID | None = None
    status: ValidationStatus
    passed: int
    failed: int
    skipped: int
    repro_fixed: bool
    regression_pass: bool
    logs_ref: str | None
    created_at: datetime


class ApprovalPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    fix_proposal_id: uuid.UUID
    approver_id: uuid.UUID
    decision: ApprovalDecision
    diff_sha256: str | None = None
    comment: str | None = None
    created_at: datetime


class ApprovalCreate(BaseModel):
    fix_proposal_id: uuid.UUID
    decision: ApprovalDecision
    diff_sha256: str | None = None
    comment: str | None = None


class FixProposalCreate(BaseModel):
    reproduction_id: uuid.UUID | None = None
    diff: str | None = None
    diff_sha256: str | None = None
    rationale: str | None = None
    risks: list[str] = Field(default_factory=list)
    files_changed: list[str] = Field(default_factory=list)
    tests_added: list[str] = Field(default_factory=list)


class FixProposalPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    investigation_id: uuid.UUID
    reproduction_id: uuid.UUID | None = None
    created_by: uuid.UUID | None = None
    status: FixProposalStatus
    diff: str | None = None
    diff_sha256: str | None = None
    rationale: str | None = None
    risks: list[str]
    files_changed: list[str]
    tests_added: list[str]
    approvals: list[ApprovalPublic] = Field(default_factory=list)
    created_at: datetime


class InvestigationDetail(InvestigationPublic):
    evidence: list[EvidencePublic]
    claims: list[ClaimPublic] = Field(default_factory=list)
    reproductions: list[ReproductionPublic] = Field(default_factory=list)
    fix_proposals: list[FixProposalPublic] = Field(default_factory=list)
    timeline: list[InvestigationTimelineItem]


class InvestigationEventPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    type: InvestigationEventType
    message: str
    details: dict[str, Any]
    created_at: datetime
