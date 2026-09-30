import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models.ticket import TicketEventType, TicketPriority, TicketStatus


class TicketCreate(BaseModel):
    customer_id: uuid.UUID
    title: str = Field(min_length=1, max_length=300)
    description: str = Field(default="", max_length=10_000)
    priority: TicketPriority = TicketPriority.MEDIUM


class TicketUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=300)
    description: str | None = Field(default=None, max_length=10_000)
    priority: TicketPriority | None = None


class TicketStatusUpdate(BaseModel):
    status: TicketStatus


class TicketCommentCreate(BaseModel):
    comment: str = Field(min_length=1, max_length=5_000)


class TicketPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    customer_id: uuid.UUID
    created_by: uuid.UUID | None
    title: str
    description: str
    priority: TicketPriority
    status: TicketStatus
    created_at: datetime
    updated_at: datetime


class TicketListResponse(BaseModel):
    items: list[TicketPublic]
    next_cursor: str | None


class TicketEventPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    ticket_id: uuid.UUID
    actor_user_id: uuid.UUID | None
    type: TicketEventType
    payload: dict[str, Any]
    created_at: datetime
