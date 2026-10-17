"""Tenant-scoped persistence for investigation records and queue jobs."""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.investigation import (
    Approval,
    Claim,
    ClaimEvidence,
    FixProposal,
    Investigation,
    InvestigationEvent,
    InvestigationJob,
    InvestigationStatus,
    PullRequest,
    Reproduction,
    ValidationRun,
)


class InvestigationRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get(
        self, organization_id: uuid.UUID, investigation_id: uuid.UUID
    ) -> Investigation | None:
        stmt = select(Investigation).where(
            Investigation.organization_id == organization_id,
            Investigation.id == investigation_id,
        )
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def active_for_ticket(
        self, organization_id: uuid.UUID, ticket_id: uuid.UUID
    ) -> Investigation | None:
        stmt = select(Investigation).where(
            Investigation.organization_id == organization_id,
            Investigation.ticket_id == ticket_id,
            Investigation.status.in_(
                [InvestigationStatus.QUEUED, InvestigationStatus.RUNNING]
            ),
        )
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def create(self, **fields: object) -> Investigation:
        investigation = Investigation(**fields)
        self.db.add(investigation)
        await self.db.flush()
        return investigation

    async def add_event(self, **fields: object) -> InvestigationEvent:
        event = InvestigationEvent(**fields)
        self.db.add(event)
        await self.db.flush()
        return event

    async def list_events(
        self, organization_id: uuid.UUID, investigation_id: uuid.UUID
    ) -> list[InvestigationEvent]:
        stmt = (
            select(InvestigationEvent)
            .where(
                InvestigationEvent.organization_id == organization_id,
                InvestigationEvent.investigation_id == investigation_id,
            )
            .order_by(InvestigationEvent.created_at, InvestigationEvent.id)
        )
        return list((await self.db.execute(stmt)).scalars().all())

    async def create_job(self, **fields: object) -> InvestigationJob:
        job = InvestigationJob(**fields)
        self.db.add(job)
        await self.db.flush()
        return job

    async def create_claim(self, **fields: object) -> Claim:
        claim = Claim(**fields)
        self.db.add(claim)
        await self.db.flush()
        return claim

    async def list_claims(
        self, organization_id: uuid.UUID, investigation_id: uuid.UUID
    ) -> list[Claim]:
        stmt = (
            select(Claim)
            .where(
                Claim.organization_id == organization_id,
                Claim.investigation_id == investigation_id,
            )
            .order_by(Claim.created_at, Claim.id)
        )
        return list((await self.db.execute(stmt)).scalars().all())

    async def create_claim_evidence(self, **fields: object) -> ClaimEvidence:
        row = ClaimEvidence(**fields)
        self.db.add(row)
        await self.db.flush()
        return row

    async def create_reproduction(self, **fields: object) -> Reproduction:
        reproduction = Reproduction(**fields)
        self.db.add(reproduction)
        await self.db.flush()
        return reproduction

    async def list_reproductions(
        self, organization_id: uuid.UUID, investigation_id: uuid.UUID
    ) -> list[Reproduction]:
        stmt = (
            select(Reproduction)
            .where(
                Reproduction.organization_id == organization_id,
                Reproduction.investigation_id == investigation_id,
            )
            .order_by(Reproduction.created_at, Reproduction.id)
        )
        return list((await self.db.execute(stmt)).scalars().all())

    async def create_validation_run(self, **fields: object) -> ValidationRun:
        run = ValidationRun(**fields)
        self.db.add(run)
        await self.db.flush()
        return run

    async def list_validation_runs(
        self,
        organization_id: uuid.UUID,
        *,
        reproduction_id: uuid.UUID | None = None,
        fix_proposal_id: uuid.UUID | None = None,
    ) -> list[ValidationRun]:
        stmt = select(ValidationRun).where(ValidationRun.organization_id == organization_id)
        if reproduction_id is not None:
            stmt = stmt.where(ValidationRun.reproduction_id == reproduction_id)
        if fix_proposal_id is not None:
            stmt = stmt.where(ValidationRun.fix_proposal_id == fix_proposal_id)
        stmt = stmt.order_by(ValidationRun.created_at, ValidationRun.id)
        return list((await self.db.execute(stmt)).scalars().all())

    async def create_fix_proposal(self, **fields: object) -> FixProposal:
        proposal = FixProposal(**fields)
        self.db.add(proposal)
        await self.db.flush()
        return proposal

    async def list_fix_proposals(
        self, organization_id: uuid.UUID, investigation_id: uuid.UUID
    ) -> list[FixProposal]:
        stmt = (
            select(FixProposal)
            .where(
                FixProposal.organization_id == organization_id,
                FixProposal.investigation_id == investigation_id,
            )
            .order_by(FixProposal.created_at, FixProposal.id)
        )
        return list((await self.db.execute(stmt)).scalars().all())

    async def create_approval(self, **fields: object) -> Approval:
        approval = Approval(**fields)
        self.db.add(approval)
        await self.db.flush()
        return approval

    async def list_approvals(
        self, organization_id: uuid.UUID, investigation_id: uuid.UUID
    ) -> list[Approval]:
        stmt = (
            select(Approval)
            .join(FixProposal, FixProposal.id == Approval.fix_proposal_id)
            .where(
                Approval.organization_id == organization_id,
                FixProposal.investigation_id == investigation_id,
            )
            .order_by(Approval.created_at, Approval.id)
        )
        return list((await self.db.execute(stmt)).scalars().all())

    async def create_pull_request(self, **fields: object) -> PullRequest:
        pr = PullRequest(**fields)
        self.db.add(pr)
        await self.db.flush()
        return pr

    async def list_pull_requests(
        self,
        organization_id: uuid.UUID,
        investigation_id: uuid.UUID | None = None,
        *,
        fix_proposal_id: uuid.UUID | None = None,
    ) -> list[PullRequest]:
        stmt = select(PullRequest).where(PullRequest.organization_id == organization_id)
        if investigation_id is not None:
            stmt = stmt.join(FixProposal, FixProposal.id == PullRequest.fix_proposal_id).where(
                FixProposal.investigation_id == investigation_id
            )
        if fix_proposal_id is not None:
            stmt = stmt.where(PullRequest.fix_proposal_id == fix_proposal_id)
        stmt = stmt.order_by(PullRequest.created_at, PullRequest.id)
        return list((await self.db.execute(stmt)).scalars().all())
