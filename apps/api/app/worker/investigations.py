"""Bounded evidence collection through MCP and the server-side ToolGateway."""

from __future__ import annotations

import re
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.agents.diagnosis import (
    Diagnosis,
    DiagnosisClient,
    DiagnosisProviderError,
    GeminiDiagnosisClient,
)
from app.core.config import Settings, get_settings
from app.core.errors import NotFoundError
from app.mcp.gateway import GatewayCallResult, GatewayContext, ToolGateway, redact_sensitive
from app.models.integration import Integration, IntegrationKind
from app.models.investigation import (
    Investigation,
    InvestigationEvent,
    InvestigationEventType,
    InvestigationJob,
    InvestigationStatus,
)
from app.models.membership import Membership, Role
from app.models.ticket import Ticket, TicketEvent, TicketEventType, TicketStatus

_READ_TOOLS = frozenset(
    {
        "code.search_code",
        "code.get_file",
        "code.get_commit",
        "code.list_commits",
        "logs.search_logs",
        "logs.get_event",
        "data.get_schema",
        "data.describe_table",
        "data.run_readonly_query",
        "deploy.get_deployment",
        "deploy.list_releases",
        "deploy.get_service_version",
        "support.get_ticket",
        "support.get_customer",
    }
)
_ERROR_TOKEN = re.compile(
    r"\b[A-Za-z_][A-Za-z0-9_]*(?:Error|Exception|Failure|Failed|Exhausted|Timeout)\b",
    re.IGNORECASE,
)
_ERROR_CODE = re.compile(r"\b[A-Z][A-Z0-9]*(?:[-_][A-Z0-9]+)+\b")
_MAX_CODE_SEARCHES = 5


def _unwrap_result(data: Any) -> Any:
    if isinstance(data, dict) and set(data) == {"result"}:
        return data["result"]
    return data


def _as_list(data: Any) -> list[Any]:
    value = _unwrap_result(data)
    if isinstance(value, list):
        return value
    return [value] if value is not None else []


def _error_messages(log_entries: list[Any]) -> list[str]:
    messages: list[str] = []
    for entry in log_entries:
        if not isinstance(entry, dict):
            continue
        message = entry.get("message")
        level = str(entry.get("level", "")).upper()
        if isinstance(message, str) and (
            level in {"ERROR", "CRITICAL"} or _ERROR_TOKEN.search(message)
        ):
            messages.append(message)
    return messages


def _error_signatures(log_entries: list[Any], *, limit: int = _MAX_CODE_SEARCHES) -> list[str]:
    signatures: list[str] = []
    seen: set[str] = set()
    for message in _error_messages(log_entries):
        for pattern in (_ERROR_TOKEN, _ERROR_CODE):
            for match in pattern.finditer(message):
                signature = match.group()
                if signature not in seen:
                    seen.add(signature)
                    signatures.append(signature)
                    if len(signatures) >= limit:
                        return signatures
    return signatures


def _candidate(
    signature: str,
    code_matches: list[Any],
    log_evidence_id: uuid.UUID | None,
    code_evidence_id: uuid.UUID | None,
) -> dict[str, Any] | None:
    matches = [line for line in code_matches if isinstance(line, dict)]
    for match in matches:
        source_line = match.get("line")
        if isinstance(source_line, str) and signature in source_line:
            return {
                "classification": "HYPOTHESIS",
                "summary": (
                    f"The error signature {signature!r} appears in both an error log "
                    f"and source code ({match.get('path')}:{match.get('line_number')}). "
                    "This is a candidate code path, not a confirmed root cause."
                ),
                "signature": signature,
                "path": match.get("path"),
                "line_number": match.get("line_number"),
                "evidence_ids": [
                    str(value) for value in (log_evidence_id, code_evidence_id) if value is not None
                ],
            }
    return None


def _configured_diagnosis_client(settings: Settings) -> tuple[DiagnosisClient | None, str | None]:
    if settings.llm_mode != "live":
        return None, None
    if not settings.llm_allow_external_data:
        return None, (
            "AI diagnosis was skipped: set LLM_ALLOW_EXTERNAL_DATA=true to permit sending "
            "redacted ticket and evidence data to the configured Gemini API."
        )
    if not settings.gemini_api_key:
        return None, "AI diagnosis was skipped: GEMINI_API_KEY is not configured."
    return (
        GeminiDiagnosisClient(api_key=settings.gemini_api_key, model=settings.llm_model),
        None,
    )


def _diagnosis_evidence(
    *,
    log_entries: list[Any],
    deployment_data: list[Any],
    commit_data: list[Any],
    code_matches: list[Any],
    log_evidence_id: uuid.UUID,
    code_evidence_ids: list[uuid.UUID],
) -> dict[str, object]:
    return {
        "log_evidence_id": str(log_evidence_id),
        "logs": [
            {
                key: value
                for key, value in item.items()
                if key in {"timestamp", "level", "service", "message"}
            }
            for item in log_entries[:20]
            if isinstance(item, dict)
        ],
        "deployment_evidence": deployment_data[:10],
        "commit_evidence": commit_data[:10],
        "code_search_evidence_ids": [str(value) for value in code_evidence_ids],
        "code_matches": code_matches[:20],
    }


def _select_code_host(
    integrations: list[Integration], selected_id: uuid.UUID | None
) -> tuple[Integration | None, str | None]:
    code_hosts = [item for item in integrations if item.kind == IntegrationKind.CODE_HOST]
    if selected_id is not None:
        selected = next((item for item in code_hosts if item.id == selected_id), None)
        if selected is None:
            return None, "The ticket's selected code-host integration is unavailable."
        return selected, None
    if len(code_hosts) == 1:
        return code_hosts[0], None
    if len(code_hosts) > 1:
        return None, "Multiple code-host integrations are configured; select one on the ticket."
    return None, None


def _ground_diagnosis(
    diagnosis: Diagnosis,
    *,
    log_evidence_id: uuid.UUID,
    code_evidence_ids: list[uuid.UUID],
    log_entries: list[Any],
    code_matches: list[Any],
) -> dict[str, Any]:
    cited_ids = set(diagnosis.evidence_ids)
    if any(value not in {log_evidence_id, *code_evidence_ids} for value in cited_ids):
        raise ValueError("Diagnosis cited an evidence ID that was not collected for this run.")
    if log_evidence_id not in cited_ids or not cited_ids.intersection(code_evidence_ids):
        raise ValueError("Diagnosis must cite collected log evidence and code-search evidence.")

    signature_in_logs = any(
        isinstance(item, dict)
        and isinstance(item.get("message"), str)
        and diagnosis.signature in item["message"]
        for item in log_entries
    )
    source_match = next(
        (
            item
            for item in code_matches
            if isinstance(item, dict)
            and item.get("path") == diagnosis.path
            and item.get("line_number") == diagnosis.line_number
            and isinstance(item.get("line"), str)
            and diagnosis.signature in item["line"]
        ),
        None,
    )
    if not signature_in_logs or source_match is None:
        raise ValueError("Diagnosis signature and source location must match collected evidence.")
    return {
        "classification": "HYPOTHESIS",
        "summary": (
            f"{diagnosis.summary} This is an AI-assisted hypothesis, not a confirmed root cause."
        ),
        "signature": diagnosis.signature,
        "path": diagnosis.path,
        "line_number": diagnosis.line_number,
        "evidence_ids": [str(value) for value in diagnosis.evidence_ids],
    }


async def collect_investigation(
    investigation_id: uuid.UUID,
    session_factory: async_sessionmaker[AsyncSession],
    gateway: ToolGateway,
) -> None:
    async with session_factory() as db:
        investigation = await db.get(Investigation, investigation_id)
        if investigation is None:
            raise NotFoundError("Queued investigation no longer exists.")
        ticket = (
            await db.execute(
                select(Ticket).where(
                    Ticket.id == investigation.ticket_id,
                    Ticket.organization_id == investigation.organization_id,
                )
            )
        ).scalar_one_or_none()
        if ticket is None:
            raise NotFoundError("Investigation ticket no longer exists.")
        membership = (
            await db.execute(
                select(Membership).where(
                    Membership.organization_id == investigation.organization_id,
                    Membership.user_id == investigation.started_by,
                )
            )
        ).scalar_one_or_none()
        if membership is None or membership.role not in {
            Role.SUPPORT,
            Role.ENGINEER,
            Role.ADMIN,
        }:
            raise PermissionError("Investigation starter no longer has permission to read tools.")

        integrations = list(
            (
                await db.execute(
                    select(Integration)
                    .where(Integration.organization_id == investigation.organization_id)
                    .order_by(Integration.name)
                )
            )
            .scalars()
            .all()
        )
        integration_ids: dict[IntegrationKind, uuid.UUID] = {}
        for integration in integrations:
            if integration.kind != IntegrationKind.CODE_HOST:
                integration_ids.setdefault(integration.kind, integration.id)
        initial_evidence_gaps: list[str] = []
        code_host, code_host_gap = _select_code_host(
            integrations, ticket.code_host_integration_id
        )
        if code_host is not None:
            integration_ids[IntegrationKind.CODE_HOST] = code_host.id
        elif code_host_gap is not None:
            initial_evidence_gaps.append(code_host_gap)

        investigation.status = InvestigationStatus.RUNNING
        investigation.started_at = datetime.now(UTC)
        db.add(
            _event(
                investigation,
                InvestigationEventType.STARTED,
                "Worker started scoped evidence collection.",
            )
        )
        await db.commit()

        context = GatewayContext(
            organization_id=investigation.organization_id,
            actor_id=investigation.started_by,
            actor_role=membership.role,
            integration_ids=integration_ids,
            allowed_tools=_READ_TOOLS,
            investigation_id=investigation.id,
        )
        evidence_ids: dict[str, uuid.UUID] = {}
        evidence_gaps = initial_evidence_gaps
        results: dict[str, GatewayCallResult] = {}

        calls: list[tuple[str, dict[str, Any], str]] = []
        if IntegrationKind.LOG_SOURCE in integration_ids:
            calls.append(("logs.search_logs", {"query": "", "limit": 100}, "logs"))
        else:
            evidence_gaps.append("No log-source integration is configured.")
        if IntegrationKind.DEPLOYMENT_SOURCE in integration_ids:
            calls.append(("deploy.list_releases", {"limit": 20}, "deployments"))
        else:
            evidence_gaps.append("No deployment-source integration is configured.")
        if IntegrationKind.CODE_HOST in integration_ids:
            calls.append(("code.list_commits", {"limit": 20}, "commits"))
        elif code_host_gap is None:
            evidence_gaps.append("No code-host integration is configured.")

        for tool_name, arguments, result_key in calls:
            result = await gateway.call_tool(tool_name, arguments, context)
            results[result_key] = result
            if result.decision.value != "ALLOW" or result.evidence_id is None:
                evidence_gaps.append(f"{tool_name}: {result.reason}")
                continue
            evidence_ids[result_key] = result.evidence_id
            items = _as_list(result.data)
            async with session_factory() as event_db:
                current = await event_db.get(Investigation, investigation.id)
                if current is not None:
                    event_db.add(
                        _event(
                            current,
                            InvestigationEventType.TOOL_COMPLETED,
                            f"Collected {len(items)} item(s) from {tool_name}.",
                            {"tool_name": tool_name, "evidence_id": str(result.evidence_id)},
                        )
                    )
                    await event_db.commit()

        log_entries = _as_list(results["logs"].data) if "logs" in results else []
        candidate = None
        code_evidence_ids: list[uuid.UUID] = []
        code_matches: list[Any] = []
        if IntegrationKind.CODE_HOST in integration_ids:
            for signature in _error_signatures(log_entries):
                code_result = await gateway.call_tool(
                    "code.search_code", {"query": signature, "limit": 20}, context
                )
                if code_result.decision.value != "ALLOW" or code_result.evidence_id is None:
                    evidence_gaps.append(f"code.search_code ({signature}): {code_result.reason}")
                    continue

                code_evidence_ids.append(code_result.evidence_id)
                matches = _as_list(code_result.data)
                code_matches.extend(matches)
                async with session_factory() as event_db:
                    current = await event_db.get(Investigation, investigation.id)
                    if current is not None:
                        event_db.add(
                            _event(
                                current,
                                InvestigationEventType.TOOL_COMPLETED,
                                f"Collected {len(code_matches)} item(s) from code.search_code.",
                                {
                                    "tool_name": "code.search_code",
                                    "query": signature,
                                    "evidence_id": str(code_result.evidence_id),
                                },
                            )
                        )
                        await event_db.commit()

                candidate = _candidate(
                    signature,
                    code_matches,
                    evidence_ids.get("logs"),
                    code_result.evidence_id,
                )
                if candidate is not None:
                    break

        diagnosis_client, diagnosis_skip_reason = _configured_diagnosis_client(get_settings())
        if diagnosis_skip_reason is not None:
            evidence_gaps.append(diagnosis_skip_reason)
        elif diagnosis_client is not None:
            log_evidence_id = evidence_ids.get("logs")
            if log_evidence_id is None or not code_evidence_ids or not code_matches:
                evidence_gaps.append(
                    "AI diagnosis was skipped: both log and matching source-code evidence are "
                    "required."
                )
            else:
                evidence = _diagnosis_evidence(
                    log_entries=log_entries,
                    deployment_data=(
                        _as_list(results["deployments"].data) if "deployments" in results else []
                    ),
                    commit_data=(_as_list(results["commits"].data) if "commits" in results else []),
                    code_matches=code_matches,
                    log_evidence_id=log_evidence_id,
                    code_evidence_ids=code_evidence_ids,
                )
                try:
                    diagnosis = await diagnosis_client.diagnose(
                        ticket_title=str(redact_sensitive(ticket.title)),
                        ticket_description=str(redact_sensitive(ticket.description)),
                        evidence=evidence,
                    )
                    candidate = _ground_diagnosis(
                        diagnosis,
                        log_evidence_id=log_evidence_id,
                        code_evidence_ids=code_evidence_ids,
                        log_entries=log_entries,
                        code_matches=code_matches,
                    )
                except (DiagnosisProviderError, ValueError) as exc:
                    evidence_gaps.append(f"AI diagnosis unavailable: {exc}")

        total_evidence_count = len(evidence_ids) + len(code_evidence_ids)
        configured_count = len(calls) + int(bool(code_evidence_ids))
        summary_parts = [
            f"Evidence collection completed for ticket {ticket.id}.",
            f"Collected {total_evidence_count} evidence item(s) across "
            f"{configured_count} configured source(s).",
        ]
        if candidate is not None:
            summary_parts.append(
                "A source-backed hypothesis is available for human review; it is not confirmed."
            )
        else:
            summary_parts.append(
                "The available evidence does not support a specific root-cause hypothesis."
            )
        if evidence_gaps:
            summary_parts.append(f"{len(evidence_gaps)} evidence gap(s) remain.")

        async with session_factory() as finish_db:
            current = await finish_db.get(Investigation, investigation.id)
            if current is None:
                raise NotFoundError("Investigation disappeared while evidence was collected.")
            current.status = InvestigationStatus.COMPLETED
            current.summary = " ".join(summary_parts)
            current.candidate = candidate
            current.evidence_gaps = evidence_gaps
            current.completed_at = datetime.now(UTC)
            finish_db.add(
                _event(
                    current,
                    InvestigationEventType.COMPLETED,
                    "Evidence collection completed.",
                    {
                        "evidence_count": total_evidence_count,
                        "evidence_gaps": len(evidence_gaps),
                        "has_hypothesis": candidate is not None,
                    },
                )
            )
            current_ticket = (
                await finish_db.execute(
                    select(Ticket)
                    .where(
                        Ticket.id == current.ticket_id,
                        Ticket.organization_id == current.organization_id,
                    )
                    .with_for_update()
                )
            ).scalar_one_or_none()
            if current_ticket is not None and current_ticket.status == TicketStatus.INVESTIGATING:
                current_ticket.status = TicketStatus.ESCALATED
                finish_db.add(
                    TicketEvent(
                        organization_id=current_ticket.organization_id,
                        ticket_id=current_ticket.id,
                        actor_user_id=None,
                        type=TicketEventType.STATUS_CHANGED,
                        payload={
                            "from": TicketStatus.INVESTIGATING.value,
                            "to": TicketStatus.ESCALATED.value,
                        },
                    )
                )
            job = (
                await finish_db.execute(
                    select(InvestigationJob).where(
                        InvestigationJob.investigation_id == investigation.id
                    )
                )
            ).scalar_one_or_none()
            if job is not None:
                job.status = "COMPLETED"
                job.locked_by = None
                job.locked_until = None
            await finish_db.commit()


def _event(
    investigation: Investigation,
    event_type: InvestigationEventType,
    message: str,
    details: dict[str, Any] | None = None,
) -> InvestigationEvent:
    return InvestigationEvent(
        organization_id=investigation.organization_id,
        investigation_id=investigation.id,
        type=event_type,
        message=message,
        details=details or {},
    )
