from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session_row
from app.core.config import Settings, get_settings
from app.core.db import get_db
from app.models.session import Session as SessionModel
from app.repositories.memberships import MembershipRepository
from app.repositories.organizations import OrganizationRepository
from app.repositories.users import UserRepository
from app.schemas.auth import (
    LoginRequest,
    MembershipPublic,
    MeResponse,
    RegisterRequest,
    SwitchOrgRequest,
    UserPublic,
)
from app.services.auth import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


def _set_session_cookie(response: Response, token: str, settings: Settings) -> None:
    response.set_cookie(
        key=settings.session_cookie_name,
        value=token,
        httponly=True,
        secure=settings.effective_session_cookie_secure,
        samesite="lax",
        max_age=settings.session_ttl_days * 24 * 3600,
        path="/",
    )


@router.post("/register", response_model=UserPublic, status_code=201)
async def register(
    body: RegisterRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> UserPublic:
    """Creates a user, a new organization, and an ADMIN membership for that

    user in it — then logs them in. There is no separate "join an existing
    organization" self-service flow; an org ADMIN adds members explicitly
    (POST /organizations/current/members).
    """
    service = AuthService(db, session_ttl_days=settings.session_ttl_days)
    user, token = await service.register(
        email=body.email, password=body.password, organization_name=body.organization_name
    )
    _set_session_cookie(response, token, settings)
    return UserPublic.model_validate(user)


@router.post("/login", response_model=UserPublic)
async def login(
    body: LoginRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> UserPublic:
    service = AuthService(db, session_ttl_days=settings.session_ttl_days)
    user, token = await service.login(email=body.email, password=body.password)
    _set_session_cookie(response, token, settings)
    return UserPublic.model_validate(user)


@router.post("/logout", status_code=204)
async def logout(
    response: Response,
    session: SessionModel = Depends(get_session_row),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> None:
    await AuthService(db).logout(token_hash=session.token_hash)
    response.delete_cookie(settings.session_cookie_name, path="/")


@router.get("/me", response_model=MeResponse)
async def me(
    session: SessionModel = Depends(get_session_row),
    db: AsyncSession = Depends(get_db),
) -> MeResponse:
    user = await UserRepository(db).get_by_id(session.user_id)
    assert user is not None  # the session's FK guarantees this

    memberships = await MembershipRepository(db).list_for_user(session.user_id)
    org_repo = OrganizationRepository(db)
    membership_views = []
    for m in memberships:
        org = await org_repo.get_by_id(m.organization_id)
        assert org is not None
        membership_views.append(
            MembershipPublic(organization_id=org.id, organization_name=org.name, role=m.role)
        )

    return MeResponse(
        user=UserPublic.model_validate(user),
        memberships=membership_views,
        active_organization_id=session.active_organization_id,
    )


@router.post("/switch-org", response_model=MeResponse)
async def switch_org(
    body: SwitchOrgRequest,
    session: SessionModel = Depends(get_session_row),
    db: AsyncSession = Depends(get_db),
) -> MeResponse:
    await AuthService(db).switch_organization(session=session, organization_id=body.organization_id)
    return await me(session, db)
