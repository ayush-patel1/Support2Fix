"""Investigation lifecycle, including atomic ticket transition and queueing."""

import uuid
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ConflictError, NotFoundError
from app.models.investigation import (
    Approval,
    ApprovalDecision,
    Claim,
    ClaimEvidence,
    ClaimKind,
    ClaimStatus,
    FixProposal,
    FixProposalStatus,
    Investigation,
    InvestigationEvent,
    InvestigationEventType,
    InvestigationStatus,
    PullRequest,
    Reproduction,
    ReproductionStatus,
    ValidationRun,
    ValidationStatus,
)
from app.models.ticket import Ticket, TicketEvent, TicketEventType, TicketStatus
from app.models.tool_call import Evidence, ToolCall
from app.repositories.investigations import InvestigationRepository
from app.schemas.investigation import (
    ApprovalCreate,
    ApprovalPublic,
    ClaimPublic,
    EvidencePublic,
    InvestigationClaimCreate,
    FixProposalCreate,
    FixProposalPublic,
    InvestigationDetail,
    InvestigationPublic,
    InvestigationTimelineItem,
    PullRequestCreate,
    PullRequestPublic,
    ReproductionPublic,
    ValidationRunPublic,
)
from app.services.tickets import ALLOWED_TRANSITIONS


def build_investigation_timeline(
    events: Sequence[InvestigationEvent],
    evidence: Sequence[EvidencePublic],
) -> list[InvestigationTimelineItem]:
    timeline = [
        InvestigationTimelineItem(
            id=event.id,
            kind="EVENT",
            occurred_at=event.created_at,
            title=event.message,
            details=event.details,
        )
        for event in events
    ]
    timeline.extend(
        InvestigationTimelineItem(
            id=item.id,
            kind="EVIDENCE",
            occurred_at=item.observed_at,
            title=f"Collected {item.kind} evidence with {item.tool_name}.",
            details={"source_ref": item.source_ref, "content_sha256": item.content_sha256},
            evidence_id=item.id,
        )
        for item in evidence
    )
    timeline.sort(key=lambda item: (item.occurred_at, str(item.id)))
    return timeline


class InvestigationService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.investigations = InvestigationRepository(db)

    async def start(
        self,
        organization_id: uuid.UUID,
        ticket_id: uuid.UUID,
        actor_id: uuid.UUID,
        *,
        idempotency_key: str | None = None,
    ) -> Investigation:
        if idempotency_key:
            existing_stmt = select(Investigation).where(
                Investigation.organization_id == organization_id,
                Investigation.idempotency_key == idempotency_key,
            )
            existing = (await self.db.execute(existing_stmt)).scalar_one_or_none()
            if existing is not None:
                if existing.ticket_id != ticket_id:
                    raise ConflictError("Idempotency-Key was already used for another ticket.")
                return existing

        ticket_stmt = (
            select(Ticket)
            .where(Ticket.id == ticket_id, Ticket.organization_id == organization_id)
            .with_for_update()
        )
        ticket = (await self.db.execute(ticket_stmt)).scalar_one_or_none()
        if ticket is None:
            raise NotFoundError("Ticket not found.")

        active = await self.investigations.active_for_ticket(organization_id, ticket_id)
        if active is not None:
            raise ConflictError("This ticket already has an active investigation.")

        if ticket.status not in {TicketStatus.OPEN, TicketStatus.ESCALATED}:
            raise ConflictError(
                f"Cannot investigate a ticket in {ticket.status.value} status."
            )
        if TicketStatus.INVESTIGATING not in ALLOWED_TRANSITIONS[ticket.status]:
            raise ConflictError(f"Ticket status {ticket.status.value} cannot be investigated.")

        previous_status = ticket.status
        investigation = await self.investigations.create(
            organization_id=organization_id,
            ticket_id=ticket.id,
            started_by=actor_id,
            status=InvestigationStatus.QUEUED,
            idempotency_key=idempotency_key,
        )
        await self.investigations.add_event(
            organization_id=organization_id,
            investigation_id=investigation.id,
            type=InvestigationEventType.QUEUED,
            message="Investigation queued for evidence collection.",
        )
        await self.investigations.create_job(
            organization_id=organization_id,
            investigation_id=investigation.id,
        )

        ticket.status = TicketStatus.INVESTIGATING
        self.db.add(
            TicketEvent(
                organization_id=organization_id,
                ticket_id=ticket.id,
                actor_user_id=actor_id,
                type=TicketEventType.STATUS_CHANGED,
                payload={"from": previous_status.value, "to": TicketStatus.INVESTIGATING.value},
            )
        )
        await self.db.commit()
        await self.db.refresh(investigation)
        return investigation

    async def get_detail(
        self, organization_id: uuid.UUID, investigation_id: uuid.UUID
    ) -> InvestigationDetail:
        investigation = await self.investigations.get(organization_id, investigation_id)
        if investigation is None:
            raise NotFoundError("Investigation not found.")

        evidence_stmt = (
            select(Evidence, ToolCall.tool_name)
            .join(
                ToolCall,
                (ToolCall.id == Evidence.tool_call_id)
                & (ToolCall.organization_id == Evidence.organization_id),
            )
            .where(
                Evidence.organization_id == organization_id,
                Evidence.investigation_id == investigation_id,
            )
            .order_by(Evidence.observed_at, Evidence.id)
            .limit(100)
        )
        rows = (await self.db.execute(evidence_stmt)).all()
        evidence = [
            EvidencePublic(
                id=item.id,
                kind=item.kind,
                source_ref=item.source_ref,
                content=item.content,
                content_sha256=item.content_sha256,
                observed_at=item.observed_at,
                tool_name=tool_name,
            )
            for item, tool_name in rows
        ]
        claims = await self.list_claims(organization_id, investigation_id)
        reproductions = await self.list_reproductions(organization_id, investigation_id)
        fix_proposals = await self.list_fix_proposals(organization_id, investigation_id)
        events = await self.investigations.list_events(organization_id, investigation_id)
        return InvestigationDetail(
            **InvestigationPublic.model_validate(investigation).model_dump(),
            evidence=evidence,
            claims=claims,
            reproductions=reproductions,
            fix_proposals=fix_proposals,
            timeline=build_investigation_timeline(events, evidence),
        )

    async def add_claim(
        self,
        organization_id: uuid.UUID,
        investigation_id: uuid.UUID,
        actor_id: uuid.UUID,
        *,
        payload: InvestigationClaimCreate,
    ) -> ClaimPublic:
        if await self.investigations.get(organization_id, investigation_id) is None:
            raise NotFoundError("Investigation not found.")

        if payload.evidence_ids:
            evidence_rows = list(
                (
                    await self.db.execute(
                        select(Evidence).where(
                            Evidence.organization_id == organization_id,
                            Evidence.investigation_id == investigation_id,
                            Evidence.id.in_(payload.evidence_ids),
                        )
                    )
                ).scalars().all()
            )
            found_ids = {row.id for row in evidence_rows}
            missing = [item for item in payload.evidence_ids if item not in found_ids]
            if missing:
                raise NotFoundError("Evidence not found for claim.")

        claim = await self.investigations.create_claim(
            organization_id=organization_id,
            investigation_id=investigation_id,
            created_by=actor_id,
            statement=payload.statement,
            kind=payload.kind,
            confidence=float(payload.confidence),
            status=ClaimStatus.PROPOSED,
        )

        evidence_quotes = payload.evidence_quotes or {}
        for evidence_id in payload.evidence_ids:
            quote = evidence_quotes.get(str(evidence_id)) or evidence_quotes.get(str(evidence_id).lower())
            if quote is None:
                quote = "" if payload.statement else ""
            await self.investigations.create_claim_evidence(
                organization_id=organization_id,
                claim_id=claim.id,
                evidence_id=evidence_id,
                quote=quote,
            )

        await self.db.commit()
        return ClaimPublic.model_validate(claim)

    async def list_claims(
        self, organization_id: uuid.UUID, investigation_id: uuid.UUID
    ) -> list[ClaimPublic]:
        if await self.investigations.get(organization_id, investigation_id) is None:
            raise NotFoundError("Investigation not found.")

        claims = await self.investigations.list_claims(organization_id, investigation_id)
        return [ClaimPublic.model_validate(claim) for claim in claims]

    async def create_reproduction(
        self,
        organization_id: uuid.UUID,
        investigation_id: uuid.UUID,
        *,
        spec: dict[str, object],
        status: ReproductionStatus = ReproductionStatus.QUEUED,
    ) -> ReproductionPublic:
        if await self.investigations.get(organization_id, investigation_id) is None:
            raise NotFoundError("Investigation not found.")

        reproduction = await self.investigations.create_reproduction(
            organization_id=organization_id,
            investigation_id=investigation_id,
            spec=spec,
            status=status,
        )
        await self.db.commit()
        return ReproductionPublic.model_validate(reproduction)

    async def list_reproductions(
        self, organization_id: uuid.UUID, investigation_id: uuid.UUID
    ) -> list[ReproductionPublic]:
        if await self.investigations.get(organization_id, investigation_id) is None:
            raise NotFoundError("Investigation not found.")

        reproductions = await self.investigations.list_reproductions(organization_id, investigation_id)
        return [ReproductionPublic.model_validate(reproduction) for reproduction in reproductions]

    async def add_validation_run(
        self,
        organization_id: uuid.UUID,
        investigation_id: uuid.UUID,
        *,
        reproduction_id: uuid.UUID | None = None,
        fix_proposal_id: uuid.UUID | None = None,
        status: ValidationStatus | str,
        passed: int = 0,
        failed: int = 0,
        skipped: int = 0,
        repro_fixed: bool = False,
        regression_pass: bool = False,
        logs_ref: str | None = None,
    ) -> ValidationRunPublic:
        if await self.investigations.get(organization_id, investigation_id) is None:
            raise NotFoundError("Investigation not found.")

        if reproduction_id is not None:
            reproduction = await self.db.get(Reproduction, reproduction_id)
            if reproduction is None or reproduction.organization_id != organization_id:
                raise NotFoundError("Reproduction not found.")
            if reproduction.investigation_id != investigation_id:
                raise ConflictError("Reproduction does not belong to the investigation.")

        if fix_proposal_id is not None:
            proposal = await self.db.get(FixProposal, fix_proposal_id)
            if proposal is None or proposal.organization_id != organization_id:
                raise NotFoundError("Fix proposal not found.")
            if proposal.investigation_id != investigation_id:
                raise ConflictError("Fix proposal does not belong to the investigation.")

        if reproduction_id is None and fix_proposal_id is None:
            raise ConflictError("A validation run must reference a reproduction or fix proposal.")

        validation_status = (
            status if isinstance(status, ValidationStatus) else ValidationStatus(status)
        )

        run = await self.investigations.create_validation_run(
            organization_id=organization_id,
            reproduction_id=reproduction_id,
            fix_proposal_id=fix_proposal_id,
            status=validation_status,
            passed=passed,
            failed=failed,
            skipped=skipped,
            repro_fixed=repro_fixed,
            regression_pass=regression_pass,
            logs_ref=logs_ref,
        )
        await self.db.commit()
        return ValidationRunPublic.model_validate(run)

    async def list_validation_runs(
        self,
        organization_id: uuid.UUID,
        investigation_id: uuid.UUID,
        *,
        reproduction_id: uuid.UUID | None = None,
        fix_proposal_id: uuid.UUID | None = None,
    ) -> list[ValidationRunPublic]:
        if await self.investigations.get(organization_id, investigation_id) is None:
            raise NotFoundError("Investigation not found.")

        if reproduction_id is not None:
            reproduction = await self.db.get(Reproduction, reproduction_id)
            if reproduction is None or reproduction.organization_id != organization_id:
                raise NotFoundError("Reproduction not found.")
            if reproduction.investigation_id != investigation_id:
                raise ConflictError("Reproduction does not belong to the investigation.")
        if fix_proposal_id is not None:
            proposal = await self.db.get(FixProposal, fix_proposal_id)
            if proposal is None or proposal.organization_id != organization_id:
                raise NotFoundError("Fix proposal not found.")
            if proposal.investigation_id != investigation_id:
                raise ConflictError("Fix proposal does not belong to the investigation.")

        runs = await self.investigations.list_validation_runs(
            organization_id,
            reproduction_id=reproduction_id,
            fix_proposal_id=fix_proposal_id,
        )
        return [ValidationRunPublic.model_validate(run) for run in runs]

    async def create_fix_proposal(
        self,
        organization_id: uuid.UUID,
        investigation_id: uuid.UUID,
        actor_id: uuid.UUID,
        *,
        payload: FixProposalCreate,
    ) -> FixProposalPublic:
        if await self.investigations.get(organization_id, investigation_id) is None:
            raise NotFoundError("Investigation not found.")
        if payload.reproduction_id is not None:
            reproduction = await self.db.get(Reproduction, payload.reproduction_id)
            if reproduction is None or reproduction.organization_id != organization_id:
                raise NotFoundError("Reproduction not found.")
            if reproduction.investigation_id != investigation_id:
                raise ConflictError("Reproduction does not belong to the investigation.")

        proposal = await self.investigations.create_fix_proposal(
            organization_id=organization_id,
            investigation_id=investigation_id,
            reproduction_id=payload.reproduction_id,
            created_by=actor_id,
            status=FixProposalStatus.DRAFT,
            diff=payload.diff,
            diff_sha256=payload.diff_sha256,
            rationale=payload.rationale,
            risks=payload.risks,
            files_changed=payload.files_changed,
            tests_added=payload.tests_added,
        )
        await self.db.commit()
        return FixProposalPublic.model_validate(proposal)

    async def list_fix_proposals(
        self, organization_id: uuid.UUID, investigation_id: uuid.UUID
    ) -> list[FixProposalPublic]:
        if await self.investigations.get(organization_id, investigation_id) is None:
            raise NotFoundError("Investigation not found.")

        proposals = await self.investigations.list_fix_proposals(organization_id, investigation_id)
        approvals = await self.investigations.list_approvals(organization_id, investigation_id)
        pull_requests = await self.investigations.list_pull_requests(organization_id, investigation_id)
        approvals_by_proposal: dict[uuid.UUID, list[ApprovalPublic]] = {}
        pull_requests_by_proposal: dict[uuid.UUID, list[PullRequestPublic]] = {}
        for approval in approvals:
            approvals_by_proposal.setdefault(approval.fix_proposal_id, []).append(
                ApprovalPublic.model_validate(approval)
            )
        for pr in pull_requests:
            pull_requests_by_proposal.setdefault(pr.fix_proposal_id, []).append(
                PullRequestPublic.model_validate(pr)
            )
        output: list[FixProposalPublic] = []
        for proposal in proposals:
            item = FixProposalPublic.model_validate(proposal)
            item.approvals = approvals_by_proposal.get(proposal.id, [])
            item.pull_requests = pull_requests_by_proposal.get(proposal.id, [])
            output.append(item)
        return output

    async def add_approval(
        self,
        organization_id: uuid.UUID,
        investigation_id: uuid.UUID,
        actor_id: uuid.UUID,
        *,
        payload: ApprovalCreate,
    ) -> ApprovalPublic:
        if await self.investigations.get(organization_id, investigation_id) is None:
            raise NotFoundError("Investigation not found.")

        proposal = await self.db.get(FixProposal, payload.fix_proposal_id)
        if proposal is None or proposal.organization_id != organization_id:
            raise NotFoundError("Fix proposal not found.")
        if proposal.investigation_id != investigation_id:
            raise ConflictError("Fix proposal does not belong to the investigation.")

        expected_hash = proposal.diff_sha256
        provided_hash = payload.diff_sha256 or expected_hash
        if expected_hash and provided_hash and expected_hash != provided_hash:
            raise ConflictError("Approval hash does not match the proposal diff.")
        if expected_hash is None and payload.diff_sha256 is not None:
            raise ConflictError("Approval hash does not match the proposal diff.")

        approval = await self.investigations.create_approval(
            organization_id=organization_id,
            fix_proposal_id=proposal.id,
            approver_id=actor_id,
            decision=payload.decision,
            diff_sha256=provided_hash,
            comment=payload.comment,
        )
        proposal.status = (
            FixProposalStatus.VALIDATED
            if payload.decision == ApprovalDecision.APPROVED
            else FixProposalStatus.REJECTED
        )
        await self.db.commit()
        await self.db.refresh(approval)
        return ApprovalPublic.model_validate(approval)

    async def list_approvals(
        self, organization_id: uuid.UUID, investigation_id: uuid.UUID
    ) -> list[ApprovalPublic]:
        if await self.investigations.get(organization_id, investigation_id) is None:
            raise NotFoundError("Investigation not found.")
        approvals = await self.investigations.list_approvals(organization_id, investigation_id)
        return [ApprovalPublic.model_validate(approval) for approval in approvals]

    async def add_pull_request(
        self,
        organization_id: uuid.UUID,
        investigation_id: uuid.UUID,
        *,
        payload: PullRequestCreate,
    ) -> PullRequestPublic:
        if await self.investigations.get(organization_id, investigation_id) is None:
            raise NotFoundError("Investigation not found.")

        proposal = await self.db.get(FixProposal, payload.fix_proposal_id)
        if proposal is None or proposal.organization_id != organization_id:
            raise NotFoundError("Fix proposal not found.")
        if proposal.investigation_id != investigation_id:
            raise ConflictError("Fix proposal does not belong to the investigation.")
        if proposal.status != FixProposalStatus.VALIDATED:
            raise ConflictError("Fix proposal must be validated before creating a pull request.")

        pr = await self.investigations.create_pull_request(
            organization_id=organization_id,
            fix_proposal_id=proposal.id,
            provider=payload.provider,
            number=payload.number,
            url=payload.url,
            branch=payload.branch,
            state=payload.state,
            title=payload.title,
        )
        await self.db.commit()
        return PullRequestPublic.model_validate(pr)

    async def list_pull_requests(
        self,
        organization_id: uuid.UUID,
        investigation_id: uuid.UUID,
        *,
        fix_proposal_id: uuid.UUID | None = None,
    ) -> list[PullRequestPublic]:
        if await self.investigations.get(organization_id, investigation_id) is None:
            raise NotFoundError("Investigation not found.")
        if fix_proposal_id is not None:
            proposal = await self.db.get(FixProposal, fix_proposal_id)
            if proposal is None or proposal.organization_id != organization_id:
                raise NotFoundError("Fix proposal not found.")
            if proposal.investigation_id != investigation_id:
                raise ConflictError("Fix proposal does not belong to the investigation.")
        prs = await self.investigations.list_pull_requests(
            organization_id,
            investigation_id,
            fix_proposal_id=fix_proposal_id,
        )
        return [PullRequestPublic.model_validate(pr) for pr in prs]

    async def list_events(
        self, organization_id: uuid.UUID, investigation_id: uuid.UUID
    ) -> list[InvestigationEvent]:
        if await self.investigations.get(organization_id, investigation_id) is None:
            raise NotFoundError("Investigation not found.")
        return await self.investigations.list_events(organization_id, investigation_id)
