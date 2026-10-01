import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models.integration import IntegrationKind, IntegrationProvider


class IntegrationCreate(BaseModel):
    kind: IntegrationKind
    provider: IntegrationProvider = IntegrationProvider.LOCAL
    name: str = Field(min_length=1, max_length=150)
    config: dict[str, Any] = Field(default_factory=dict)


class IntegrationUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=150)
    config: dict[str, Any] | None = None


class IntegrationPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    kind: IntegrationKind
    provider: IntegrationProvider
    name: str
    config: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class IntegrationTestResult(BaseModel):
    ok: bool
    detail: str
