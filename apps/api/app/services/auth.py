"""Registration, login, logout and org-switching. Routes call this; nothing

here knows about HTTP (status codes, cookies) — see app/api/v1/auth.py for
that boundary. Raises app.core.errors.AppError subclasses on failure.
"""

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AlreadyExistsError, ForbiddenError, InvalidCredentialsError
from app.core.security import (
    generate_session_token,
    hash_password,
    hash_session_token,
    verify_password,
)
from app.models.membership import Role
from app.models.session import Session
from app.models.user import User
from app.repositories.memberships import MembershipRepository
from app.repositories.organizations import OrganizationRepository
from app.repositories.sessions import SessionRepository
from app.repositories.users import UserRepository


class AuthService:
    def __init__(self, db: AsyncSession, *, session_ttl_days: int = 7) -> None:
        self.db = db
        self.session_ttl_days = session_ttl_days
        self.users = UserRepository(db)
        self.organizations = OrganizationRepository(db)
        self.memberships = MembershipRepository(db)
        self.sessions = SessionRepository(db)

    async def register(
        self, *, email: str, password: str, organization_name: str
    ) -> tuple[User, str]:
        if await self.users.get_by_email(email) is not None:
            raise AlreadyExistsError("An account with that email already exists.")

        user = await self.users.create(email=email, password_hash=hash_password(password))
        org = await self.organizations.create(name=organization_name)
        await self.memberships.create(user_id=user.id, organization_id=org.id, role=Role.ADMIN)

        token = await self._create_session(user.id, active_organization_id=org.id)
        await self.db.commit()
        return user, token

    async def login(self, *, email: str, password: str) -> tuple[User, str]:
        user = await self.users.get_by_email(email)
        # Same error for "no such user" and "wrong password" — don't let a
        # caller distinguish the two (see security.md §10).
        if user is None or not user.is_active or not verify_password(password, user.password_hash):
            raise InvalidCredentialsError("Invalid email or password.")

        memberships = await self.memberships.list_for_user(user.id)
        active_org_id = memberships[0].organization_id if memberships else None

        token = await self._create_session(user.id, active_organization_id=active_org_id)
        await self.db.commit()
        return user, token

    async def logout(self, *, token_hash: str) -> None:
        await self.sessions.delete_by_token_hash(token_hash)
        await self.db.commit()

    async def switch_organization(self, *, session: Session, organization_id: uuid.UUID) -> None:
        membership = await self.memberships.get(session.user_id, organization_id)
        if membership is None:
            raise ForbiddenError("You are not a member of that organization.")
        await self.sessions.set_active_organization(session, organization_id)
        await self.db.commit()

    async def _create_session(
        self, user_id: uuid.UUID, *, active_organization_id: uuid.UUID | None
    ) -> str:
        raw_token = generate_session_token()
        expires_at = datetime.now(UTC) + timedelta(days=self.session_ttl_days)
        await self.sessions.create(
            user_id=user_id,
            token_hash=hash_session_token(raw_token),
            active_organization_id=active_organization_id,
            expires_at=expires_at,
        )
        return raw_token
