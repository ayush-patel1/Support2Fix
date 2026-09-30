import uuid

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.membership import Role


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=200)
    organization_name: str = Field(min_length=1, max_length=200)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class SwitchOrgRequest(BaseModel):
    organization_id: uuid.UUID


class UserPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    is_active: bool


class MembershipPublic(BaseModel):
    organization_id: uuid.UUID
    organization_name: str
    role: Role


class MeResponse(BaseModel):
    user: UserPublic
    memberships: list[MembershipPublic]
    active_organization_id: uuid.UUID | None
