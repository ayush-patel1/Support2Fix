"""Authenticated investigation start, status, evidence, and timeline APIs."""

from uuid import UUID

from fastapi import APIRouter, Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import OrgContext, get_org_context, require_any_role, require_role
from app.core.db import get_db
from app.core.errors import NotFoundError
from app.models.investigation import InvestigationEvent
from app.models.membership import Role
from app.schemas.investigation import (
    ApprovalCreate,
    ApprovalPublic,
    FixProposalCreate,
    FixProposalPublic,
    InvestigationClaimCreate,
    InvestigationDetail,
    InvestigationEventPublic,
    InvestigationPublic,
    ClaimPublic,
    PullRequestCreate,
    PullRequestPublic,
    ReproductionPublic,
    ValidationRunPublic,
)
from app.services.investigations import InvestigationService

router = APIRouter(tags=["investigations"])


@router.post(
    "/tickets/{ticket_id}/investigations",
    response_model=InvestigationPublic,
    status_code=202,
)
async def start_investigation(
    ticket_id: UUID,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key", max_length=128),
    ctx: OrgContext = Depends(require_role(Role.SUPPORT)),
    db: AsyncSession = Depends(get_db),
) -> InvestigationPublic:
    investigation = await InvestigationService(db).start(
        ctx.organization_id,
        ticket_id,
        ctx.user_id,
        idempotency_key=idempotency_key,
    )
    return InvestigationPublic.model_validate(investigation)


@router.get("/investigations/{investigation_id}", response_model=InvestigationDetail)
async def get_investigation(
    investigation_id: UUID,
    ctx: OrgContext = Depends(get_org_context),
    db: AsyncSession = Depends(get_db),
) -> InvestigationDetail:
    return await InvestigationService(db).get_detail(ctx.organization_id, investigation_id)


@router.get(
    "/investigations/{investigation_id}/claims",
    response_model=list[ClaimPublic],
)
async def list_investigation_claims(
    investigation_id: UUID,
    ctx: OrgContext = Depends(get_org_context),
    db: AsyncSession = Depends(get_db),
) -> list[ClaimPublic]:
    return await InvestigationService(db).list_claims(ctx.organization_id, investigation_id)


@router.post(
    "/investigations/{investigation_id}/claims",
    response_model=ClaimPublic,
    status_code=201,
)
async def add_investigation_claim(
    investigation_id: UUID,
    payload: InvestigationClaimCreate,
    ctx: OrgContext = Depends(get_org_context),
    db: AsyncSession = Depends(get_db),
) -> ClaimPublic:
    return await InvestigationService(db).add_claim(
        ctx.organization_id,
        investigation_id,
        ctx.user_id,
        payload=payload,
    )


@router.get(
    "/investigations/{investigation_id}/reproductions",
    response_model=list[ReproductionPublic],
)
async def list_investigation_reproductions(
    investigation_id: UUID,
    ctx: OrgContext = Depends(get_org_context),
    db: AsyncSession = Depends(get_db),
) -> list[ReproductionPublic]:
    return await InvestigationService(db).list_reproductions(ctx.organization_id, investigation_id)


@router.post(
    "/investigations/{investigation_id}/reproductions",
    response_model=ReproductionPublic,
    status_code=201,
)
async def create_investigation_reproduction(
    investigation_id: UUID,
    payload: dict,
    ctx: OrgContext = Depends(get_org_context),
    db: AsyncSession = Depends(get_db),
) -> ReproductionPublic:
    return await InvestigationService(db).create_reproduction(
        ctx.organization_id,
        investigation_id,
        spec=payload,
    )


@router.get(
    "/investigations/{investigation_id}/reproductions/{reproduction_id}/validation",
    response_model=list[ValidationRunPublic],
)
async def list_reproduction_validation_runs(
    investigation_id: UUID,
    reproduction_id: UUID,
    ctx: OrgContext = Depends(get_org_context),
    db: AsyncSession = Depends(get_db),
) -> list[ValidationRunPublic]:
    return await InvestigationService(db).list_validation_runs(
        ctx.organization_id,
        investigation_id,
        reproduction_id=reproduction_id,
    )


@router.post(
    "/investigations/{investigation_id}/reproductions/{reproduction_id}/validation",
    response_model=ValidationRunPublic,
    status_code=201,
)
async def create_reproduction_validation_run(
    investigation_id: UUID,
    reproduction_id: UUID,
    payload: dict,
    ctx: OrgContext = Depends(get_org_context),
    db: AsyncSession = Depends(get_db),
) -> ValidationRunPublic:
    return await InvestigationService(db).add_validation_run(
        ctx.organization_id,
        investigation_id,
        reproduction_id=reproduction_id,
        status=payload.get("status", "PASSED"),
        passed=int(payload.get("passed", 0)),
        failed=int(payload.get("failed", 0)),
        skipped=int(payload.get("skipped", 0)),
        repro_fixed=bool(payload.get("repro_fixed", False)),
        regression_pass=bool(payload.get("regression_pass", False)),
        logs_ref=payload.get("logs_ref"),
    )


@router.get(
    "/investigations/{investigation_id}/fix-proposals",
    response_model=list[FixProposalPublic],
)
async def list_fix_proposals(
    investigation_id: UUID,
    ctx: OrgContext = Depends(get_org_context),
    db: AsyncSession = Depends(get_db),
) -> list[FixProposalPublic]:
    return await InvestigationService(db).list_fix_proposals(ctx.organization_id, investigation_id)


@router.post(
    "/investigations/{investigation_id}/fix-proposals",
    response_model=FixProposalPublic,
    status_code=201,
)
async def create_fix_proposal(
    investigation_id: UUID,
    payload: FixProposalCreate,
    ctx: OrgContext = Depends(get_org_context),
    db: AsyncSession = Depends(get_db),
) -> FixProposalPublic:
    return await InvestigationService(db).create_fix_proposal(
        ctx.organization_id,
        investigation_id,
        ctx.user_id,
        payload=payload,
    )


@router.get(
    "/investigations/{investigation_id}/fix-proposals/{fix_proposal_id}/validation",
    response_model=list[ValidationRunPublic],
)
async def list_fix_proposal_validation_runs(
    investigation_id: UUID,
    fix_proposal_id: UUID,
    ctx: OrgContext = Depends(get_org_context),
    db: AsyncSession = Depends(get_db),
) -> list[ValidationRunPublic]:
    return await InvestigationService(db).list_validation_runs(
        ctx.organization_id,
        investigation_id,
        fix_proposal_id=fix_proposal_id,
    )


@router.post(
    "/investigations/{investigation_id}/fix-proposals/{fix_proposal_id}/validation",
    response_model=ValidationRunPublic,
    status_code=201,
)
async def create_fix_proposal_validation_run(
    investigation_id: UUID,
    fix_proposal_id: UUID,
    payload: dict,
    ctx: OrgContext = Depends(get_org_context),
    db: AsyncSession = Depends(get_db),
) -> ValidationRunPublic:
    return await InvestigationService(db).add_validation_run(
        ctx.organization_id,
        investigation_id,
        fix_proposal_id=fix_proposal_id,
        status=payload.get("status", "PASSED"),
        passed=int(payload.get("passed", 0)),
        failed=int(payload.get("failed", 0)),
        skipped=int(payload.get("skipped", 0)),
        repro_fixed=bool(payload.get("repro_fixed", False)),
        regression_pass=bool(payload.get("regression_pass", False)),
        logs_ref=payload.get("logs_ref"),
    )


@router.get(
    "/investigations/{investigation_id}/approvals",
    response_model=list[ApprovalPublic],
)
async def list_investigation_approvals(
    investigation_id: UUID,
    ctx: OrgContext = Depends(get_org_context),
    db: AsyncSession = Depends(get_db),
) -> list[ApprovalPublic]:
    return await InvestigationService(db).list_approvals(ctx.organization_id, investigation_id)


@router.post(
    "/investigations/{investigation_id}/approvals",
    response_model=ApprovalPublic,
    status_code=201,
)
async def create_investigation_approval(
    investigation_id: UUID,
    body: ApprovalCreate,
    ctx: OrgContext = Depends(require_any_role(Role.ENGINEER, Role.ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> ApprovalPublic:
    return await InvestigationService(db).add_approval(
        ctx.organization_id,
        investigation_id,
        ctx.user_id,
        payload=body,
    )


@router.get(
    "/investigations/{investigation_id}/pull-requests",
    response_model=list[PullRequestPublic],
)
async def list_investigation_pull_requests(
    investigation_id: UUID,
    ctx: OrgContext = Depends(get_org_context),
    db: AsyncSession = Depends(get_db),
) -> list[PullRequestPublic]:
    return await InvestigationService(db).list_pull_requests(ctx.organization_id, investigation_id)


@router.post(
    "/investigations/{investigation_id}/pull-requests",
    response_model=PullRequestPublic,
    status_code=201,
)
async def create_investigation_pull_request(
    investigation_id: UUID,
    body: PullRequestCreate,
    ctx: OrgContext = Depends(require_any_role(Role.ENGINEER, Role.ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> PullRequestPublic:
    return await InvestigationService(db).add_pull_request(
        ctx.organization_id,
        investigation_id,
        payload=body,
    )


@router.get(
    "/investigations/{investigation_id}/fix-proposals/{fix_proposal_id}/pull-requests",
    response_model=list[PullRequestPublic],
)
async def list_fix_proposal_pull_requests(
    investigation_id: UUID,
    fix_proposal_id: UUID,
    ctx: OrgContext = Depends(get_org_context),
    db: AsyncSession = Depends(get_db),
) -> list[PullRequestPublic]:
    return await InvestigationService(db).list_pull_requests(
        ctx.organization_id,
        investigation_id,
        fix_proposal_id=fix_proposal_id,
    )


@router.post(
    "/investigations/{investigation_id}/fix-proposals/{fix_proposal_id}/pull-requests",
    response_model=PullRequestPublic,
    status_code=201,
)
async def create_fix_proposal_pull_request(
    investigation_id: UUID,
    fix_proposal_id: UUID,
    body: PullRequestCreate,
    ctx: OrgContext = Depends(require_any_role(Role.ENGINEER, Role.ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> PullRequestPublic:
    body.fix_proposal_id = fix_proposal_id
    return await InvestigationService(db).add_pull_request(
        ctx.organization_id,
        investigation_id,
        payload=body,
    )


@router.get(
    "/investigations/{investigation_id}/events",
    response_model=list[InvestigationEventPublic],
)
async def list_investigation_events(
    investigation_id: UUID,
    ctx: OrgContext = Depends(get_org_context),
    db: AsyncSession = Depends(get_db),
) -> list[InvestigationEventPublic]:
    events: list[InvestigationEvent] = await InvestigationService(db).list_events(
        ctx.organization_id, investigation_id
    )
    return [InvestigationEventPublic.model_validate(event) for event in events]
