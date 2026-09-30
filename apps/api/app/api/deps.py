"""FastAPI dependencies for session/tenant auth. See security.md §4, §10-11

and system-design.md §7.1 ("Tenant context").

Every tenant-scoped route depends on `get_org_context` (directly or via
`require_role`/`require_any_role`), which is what makes cross-tenant access
impossible at the route layer: the organization id always comes from the
caller's own session, never from a client-supplied header or body field.
"""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.db import get_db
from app.core.errors import AuthenticationRequiredError, ForbiddenError, NoActiveOrganizationError
from app.core.security import hash_session_token
from app.models.membership import ROLE_ORDER, Role
from app.models.session import Session as SessionModel
from app.repositories.memberships import MembershipRepository
from app.repositories.sessions import SessionRepository


@dataclass(frozen=True)
class OrgContext:
    user_id: UUID
    organization_id: UUID
    role: Role


async def get_session_row(
    request: Request,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> SessionModel:
    token = request.cookies.get(settings.session_cookie_name)
    if not token:
        raise AuthenticationRequiredError("Not authenticated.")

    repo = SessionRepository(db)
    session = await repo.get_by_token_hash(hash_session_token(token))
    if session is None:
        raise AuthenticationRequiredError("Session not found or already logged out.")

    now = datetime.now(UTC)
    idle_cutoff = session.last_seen_at + timedelta(hours=settings.session_idle_timeout_hours)
    if session.expires_at < now or idle_cutoff < now:
        await repo.delete(session)
        raise AuthenticationRequiredError("Session expired.")

    await repo.touch(session)
    return session


async def get_org_context(
    session: SessionModel = Depends(get_session_row),
    db: AsyncSession = Depends(get_db),
) -> OrgContext:
    if session.active_organization_id is None:
        raise NoActiveOrganizationError("No active organization selected.")

    membership = await MembershipRepository(db).get(session.user_id, session.active_organization_id)
    if membership is None:
        # The session pointed at an org the user is no longer a member of
        # (e.g. they were removed). Fail closed.
        raise NoActiveOrganizationError("No active organization selected.")

    return OrgContext(
        user_id=session.user_id,
        organization_id=session.active_organization_id,
        role=membership.role,
    )


def require_role(min_role: Role) -> Callable[[OrgContext], Awaitable[OrgContext]]:
    """Hierarchy check: VIEWER < SUPPORT < ENGINEER < ADMIN."""

    async def _dependency(ctx: OrgContext = Depends(get_org_context)) -> OrgContext:
        if ROLE_ORDER[ctx.role] < ROLE_ORDER[min_role]:
            raise ForbiddenError(f"Requires at least the {min_role.value} role.")
        return ctx

    return _dependency


def require_any_role(*allowed: Role) -> Callable[[OrgContext], Awaitable[OrgContext]]:
    """Exact-set check, for capabilities that don't follow the linear

    hierarchy (e.g. ADMIN + ENGINEER can approve a fix, but SUPPORT can't,
    even though SUPPORT outranks VIEWER) — see security.md §4.
    """

    async def _dependency(ctx: OrgContext = Depends(get_org_context)) -> OrgContext:
        if ctx.role not in allowed:
            names = ", ".join(r.value for r in allowed)
            raise ForbiddenError(f"Requires one of: {names}.")
        return ctx

    return _dependency
