import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.membership import Role


class OrganizationPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    slug: str
    created_at: datetime


class OrganizationUpdate(BaseModel):
    # Settings beyond the name are introduced as concrete needs arrive
    # (e.g. tool-permission overrides in Phase 8) rather than as a
    # free-form JSON blob now.
    name: str = Field(min_length=1, max_length=200)


class MemberPublic(BaseModel):
    user_id: uuid.UUID
    email: str
    role: Role


class AddMemberRequest(BaseModel):
    email: EmailStr
    role: Role = Role.VIEWER


class UpdateMemberRoleRequest(BaseModel):
    role: Role
