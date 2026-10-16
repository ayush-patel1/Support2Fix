"""Bounded evidence collection through MCP and the server-side ToolGateway."""

from __future__ import annotations

import re
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.errors import NotFoundError
from app.mcp.gateway import GatewayCallResult, GatewayContext, ToolGateway
from app.models.integration import Integration, IntegrationKind
from app.models.investigation import (
    Investigation,
    InvestigationEvent,
    InvestigationEventType,
    InvestigationJob,
    InvestigationStatus,
)
from app.models.membership import Membership, Role
from app.models.ticket import Ticket

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
    r"\b[A-Za-z_][A-Za-z0-9_]*(?:Error|Exception|Failure|Failed|Exhausted|Timeout)\b"
)


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


def _candidate(
    log_entries: list[Any], code_matches: list[Any], log_evidence_id: uuid.UUID | None,
    code_evidence_id: uuid.UUID | None,
) -> dict[str, Any] | None:
    messages = _error_messages(log_entries)
    matches = [line for line in code_matches if isinstance(line, dict)]
    for message in messages:
        for signature in _ERROR_TOKEN.findall(message):
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
                            str(value)
                            for value in (log_evidence_id, code_evidence_id)
                            if value is not None
                        ],
                    }
    return None


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
            integration_ids.setdefault(integration.kind, integration.id)

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
        evidence_gaps: list[str] = []
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
        else:
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
        error_signatures = [
            signature
            for message in _error_messages(log_entries)
            for signature in _ERROR_TOKEN.findall(message)
        ]
        if IntegrationKind.CODE_HOST in integration_ids and error_signatures:
            signature = error_signatures[0]
            code_result = await gateway.call_tool(
                "code.search_code", {"query": signature, "limit": 20}, context
            )
            results["code_search"] = code_result
            if code_result.decision.value == "ALLOW" and code_result.evidence_id is not None:
                evidence_ids["code_search"] = code_result.evidence_id
            else:
                evidence_gaps.append(f"code.search_code: {code_result.reason}")

        code_matches = (
            _as_list(results["code_search"].data) if "code_search" in results else []
        )
        candidate = _candidate(
            log_entries,
            code_matches,
            evidence_ids.get("logs"),
            evidence_ids.get("code_search"),
        )

        configured_count = len(calls)
        summary_parts = [
            f"Evidence collection completed for ticket {ticket.id}.",
            f"Collected {len(evidence_ids)} evidence item(s) across "
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
                        "evidence_count": len(evidence_ids),
                        "evidence_gaps": len(evidence_gaps),
                        "has_hypothesis": candidate is not None,
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
