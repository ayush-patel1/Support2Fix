import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

from app.models.investigation import InvestigationEventType, InvestigationStatus


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


class InvestigationDetail(InvestigationPublic):
    evidence: list[EvidencePublic]
    timeline: list[InvestigationTimelineItem]


class InvestigationEventPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    type: InvestigationEventType
    message: str
    details: dict[str, Any]
    created_at: datetime
