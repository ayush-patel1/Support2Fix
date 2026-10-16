"""Server-side tool policy and tenant-scope enforcement for MCP calls."""

from __future__ import annotations

import asyncio
import hashlib
import json
import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Protocol
from uuid import UUID

from httpx2 import TransportError
from jsonschema import Draft202012Validator
from mcp.shared.exceptions import MCPError

from app.core.ids import uuid7
from app.models.integration import IntegrationKind
from app.models.membership import Role
from app.models.tool_call import Evidence, ToolCall


class ToolRisk(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class PolicyDecision(StrEnum):
    ALLOW = "ALLOW"
    DENY = "DENY"
    REQUIRE_APPROVAL = "REQUIRE_APPROVAL"


@dataclass(frozen=True)
class ToolPolicy:
    risk: ToolRisk
    allowed_actor_roles: frozenset[Role]
    idempotent: bool = True
    timeout_seconds: int = 20
    max_result_bytes: int = 65_536


@dataclass(frozen=True)
class ApprovalGrant:
    tool_name: str
    approver_role: Role
    arguments_sha256: str | None = None
    artifact_sha256: str | None = None


@dataclass(frozen=True)
class GatewayContext:
    organization_id: UUID
    actor_id: UUID
    actor_role: Role
    integration_ids: Mapping[IntegrationKind, UUID]
    allowed_tools: frozenset[str]
    investigation_id: UUID | None = None
    validated_artifact_sha256: str | None = None


@dataclass(frozen=True)
class PolicyResult:
    decision: PolicyDecision
    reason: str


@dataclass(frozen=True)
class GatewayCallResult:
    decision: PolicyDecision
    reason: str
    evidence_id: UUID | None = None
    data: Any = None
    untrusted_data: str | None = None


class MCPTool(Protocol):
    name: str
    input_schema: dict[str, Any]
    output_schema: dict[str, Any] | None
    description: str | None


class MCPClient(Protocol):
    async def list_tools(self) -> Any: ...

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> Any: ...


_READ_ROLES = frozenset({Role.SUPPORT, Role.ENGINEER, Role.ADMIN})
_APPROVER_ROLES = frozenset({Role.ENGINEER, Role.ADMIN})
_TOOL_POLICIES: dict[str, ToolPolicy] = {
    name: ToolPolicy(ToolRisk.LOW, _READ_ROLES)
    for name in (
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
    )
}
_TOOL_POLICIES["code.create_branch"] = ToolPolicy(ToolRisk.MEDIUM, _READ_ROLES, idempotent=False)
_TOOL_POLICIES["code.create_pull_request"] = ToolPolicy(
    ToolRisk.HIGH, _APPROVER_ROLES, idempotent=False
)

_TOOL_INTEGRATION_KINDS: dict[str, IntegrationKind] = {
    "code.": IntegrationKind.CODE_HOST,
    "logs.": IntegrationKind.LOG_SOURCE,
    "data.": IntegrationKind.DATA_SOURCE,
    "deploy.": IntegrationKind.DEPLOYMENT_SOURCE,
    "support.": IntegrationKind.SUPPORT_SOURCE,
}
_TENANT_ARGUMENTS = frozenset({"organization_id", "integration_id"})
_SENSITIVE_KEYS = ("password", "token", "secret", "api_key", "access_key", "email", "phone")
_EMAIL_PATTERN = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
_BEARER_PATTERN = re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/-]+=*")


def tool_policies() -> Mapping[str, ToolPolicy]:
    """Return the server-side policy catalog."""
    return _TOOL_POLICIES.copy()


def canonical_arguments_sha256(arguments: Mapping[str, Any]) -> str:
    trusted_arguments = {
        key: value for key, value in arguments.items() if key not in _TENANT_ARGUMENTS
    }
    encoded = json.dumps(
        trusted_arguments, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    )
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def validate_and_inject_arguments(
    tool_name: str,
    arguments: Mapping[str, Any],
    input_schema: Mapping[str, Any],
    context: GatewayContext,
) -> dict[str, Any]:
    """Validate untrusted arguments and overwrite tenant scope from context."""
    if tool_name not in _TOOL_POLICIES:
        raise ValueError(f"Unknown tool: {tool_name}")
    if not isinstance(arguments, Mapping):
        raise ValueError("Tool arguments must be an object.")

    integration_kind = next(
        (kind for prefix, kind in _TOOL_INTEGRATION_KINDS.items() if tool_name.startswith(prefix)),
        None,
    )
    if integration_kind is None:
        raise ValueError(f"Tool has no integration mapping: {tool_name}")
    integration_id = context.integration_ids.get(integration_kind)
    if integration_id is None:
        raise ValueError(f"No trusted {integration_kind.value} integration is configured.")

    properties = input_schema.get("properties", {})
    if not isinstance(properties, Mapping):
        raise ValueError("Tool input schema has invalid properties.")
    supplied_arguments = {
        key: value for key, value in arguments.items() if key not in _TENANT_ARGUMENTS
    }
    unknown_arguments = supplied_arguments.keys() - properties.keys()
    if unknown_arguments:
        raise ValueError(f"Unknown tool argument(s): {', '.join(sorted(unknown_arguments))}.")

    model_schema = dict(input_schema)
    model_schema["properties"] = {
        key: value for key, value in properties.items() if key not in _TENANT_ARGUMENTS
    }
    model_schema["required"] = [
        key for key in input_schema.get("required", []) if key not in _TENANT_ARGUMENTS
    ]
    Draft202012Validator.check_schema(model_schema)
    errors = sorted(Draft202012Validator(model_schema).iter_errors(supplied_arguments), key=str)
    if errors:
        raise ValueError(f"Invalid tool arguments: {errors[0].message}")

    injected = dict(supplied_arguments)
    injected["organization_id"] = str(context.organization_id)
    injected["integration_id"] = str(integration_id)
    Draft202012Validator.check_schema(input_schema)
    errors = sorted(Draft202012Validator(input_schema).iter_errors(injected), key=str)
    if errors:
        raise ValueError(f"Invalid trusted tool scope: {errors[0].message}")
    return injected


def evaluate_tool_policy(
    tool_name: str,
    arguments: Mapping[str, Any],
    context: GatewayContext,
    approval: ApprovalGrant | None = None,
) -> PolicyResult:
    policy = _TOOL_POLICIES.get(tool_name)
    if policy is None:
        return PolicyResult(PolicyDecision.DENY, "Tool is not registered.")
    if tool_name not in context.allowed_tools:
        return PolicyResult(PolicyDecision.DENY, "Tool is outside this node's capability set.")
    if context.actor_role not in policy.allowed_actor_roles:
        return PolicyResult(PolicyDecision.DENY, "Actor role is not permitted for this tool.")
    if policy.risk is ToolRisk.CRITICAL:
        return PolicyResult(PolicyDecision.DENY, "CRITICAL tools are disabled.")
    if policy.risk is ToolRisk.LOW:
        return PolicyResult(PolicyDecision.ALLOW, "LOW-risk read tool.")
    if approval is None:
        return PolicyResult(PolicyDecision.REQUIRE_APPROVAL, "An explicit approval is required.")
    if approval.tool_name != tool_name or approval.approver_role not in _APPROVER_ROLES:
        return PolicyResult(PolicyDecision.DENY, "Approval does not authorize this tool.")
    if policy.risk is ToolRisk.MEDIUM:
        if approval.arguments_sha256 != canonical_arguments_sha256(arguments):
            return PolicyResult(PolicyDecision.DENY, "Approval does not match these arguments.")
        return PolicyResult(PolicyDecision.ALLOW, "MEDIUM-risk call has a matching approval.")
    if (
        context.validated_artifact_sha256 is None
        or approval.artifact_sha256 != context.validated_artifact_sha256
    ):
        return PolicyResult(PolicyDecision.DENY, "Approval does not match a validated artifact.")
    return PolicyResult(
        PolicyDecision.ALLOW, "HIGH-risk call has approval for the validated artifact."
    )


def redact_sensitive(value: Any, *, key: str = "") -> Any:
    if any(sensitive in key.lower() for sensitive in _SENSITIVE_KEYS):
        return "[REDACTED]"
    if isinstance(value, dict):
        return {str(name): redact_sensitive(item, key=str(name)) for name, item in value.items()}
    if isinstance(value, list):
        return [redact_sensitive(item) for item in value]
    if isinstance(value, str):
        value = _BEARER_PATTERN.sub("Bearer [REDACTED]", value)
        return _EMAIL_PATTERN.sub("[REDACTED_EMAIL]", value)
    return value


def _tool_integration_kind(tool_name: str) -> IntegrationKind | None:
    return next(
        (kind for prefix, kind in _TOOL_INTEGRATION_KINDS.items() if tool_name.startswith(prefix)),
        None,
    )


def _without_tenant_properties(schema: Mapping[str, Any]) -> dict[str, Any]:
    result = dict(schema)
    properties = schema.get("properties", {})
    if isinstance(properties, Mapping):
        result["properties"] = {
            key: value for key, value in properties.items() if key not in _TENANT_ARGUMENTS
        }
    result["required"] = [key for key in schema.get("required", []) if key not in _TENANT_ARGUMENTS]
    result["additionalProperties"] = False
    return result


def _bounded_json(value: Any, max_bytes: int) -> tuple[Any, str]:
    serialized = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    encoded = serialized.encode("utf-8")
    if len(encoded) <= max_bytes:
        return value, serialized
    preview = encoded[: max(0, (max_bytes - 64) // 2)].decode("utf-8", errors="ignore")
    bounded = {"truncated": True, "preview": preview}
    return bounded, json.dumps(
        bounded, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    )


class ToolGateway:
    """Enforce server-side policy around a worker's MCP client session."""

    def __init__(
        self,
        client: MCPClient,
        session_factory: Callable[[], Any],
    ) -> None:
        self._client = client
        self._session_factory = session_factory

    async def list_tools(self, context: GatewayContext) -> list[dict[str, Any]]:
        available = (await self._client.list_tools()).tools
        definitions: list[dict[str, Any]] = []
        for tool in available:
            policy = _TOOL_POLICIES.get(tool.name)
            integration_kind = _tool_integration_kind(tool.name)
            if (
                policy is None
                or integration_kind is None
                or integration_kind not in context.integration_ids
                or tool.name not in context.allowed_tools
                or context.actor_role not in policy.allowed_actor_roles
            ):
                continue
            definitions.append(
                {
                    "name": tool.name,
                    "description": tool.description or "",
                    "input_schema": _without_tenant_properties(tool.input_schema),
                    "risk": policy.risk.value,
                }
            )
        return definitions

    async def call_tool(
        self,
        tool_name: str,
        arguments: Mapping[str, Any],
        context: GatewayContext,
        approval: ApprovalGrant | None = None,
    ) -> GatewayCallResult:
        policy = _TOOL_POLICIES.get(tool_name)
        if policy is None:
            result = PolicyResult(PolicyDecision.DENY, "Tool is not registered.")
            await self._record_call(tool_name, {}, context, result, None, result.reason)
            return GatewayCallResult(result.decision, result.reason)

        tool_list = (await self._client.list_tools()).tools
        tool = next((item for item in tool_list if item.name == tool_name), None)
        if tool is None:
            result = PolicyResult(PolicyDecision.DENY, "Tool is not available from the MCP server.")
            await self._record_call(tool_name, {}, context, result, None, result.reason)
            return GatewayCallResult(result.decision, result.reason)

        try:
            injected_arguments = validate_and_inject_arguments(
                tool_name, arguments, tool.input_schema, context
            )
        except (TypeError, ValueError) as exc:
            result = PolicyResult(PolicyDecision.DENY, str(exc))
            await self._record_call(tool_name, arguments, context, result, None, result.reason)
            return GatewayCallResult(result.decision, result.reason)

        policy_result = evaluate_tool_policy(tool_name, arguments, context, approval)
        if policy_result.decision is not PolicyDecision.ALLOW:
            await self._record_call(
                tool_name, arguments, context, policy_result, None, policy_result.reason
            )
            return GatewayCallResult(policy_result.decision, policy_result.reason)

        response = None
        execution_error: Exception | None = None
        max_attempts = 2 if policy.idempotent else 1
        attempts_made = 0
        for attempt in range(max_attempts):
            attempts_made = attempt + 1
            try:
                async with asyncio.timeout(policy.timeout_seconds):
                    response = await self._client.call_tool(tool_name, injected_arguments)
                break
            except (TimeoutError, TransportError) as exc:
                execution_error = exc
                if attempt + 1 >= max_attempts:
                    break
            except MCPError as exc:
                execution_error = exc
                break
        if response is None:
            error_type = (
                type(execution_error).__name__ if execution_error is not None else "unknown"
            )
            reason = f"Tool execution failed after {attempts_made} attempt(s): {error_type}."
            failed = PolicyResult(PolicyDecision.DENY, reason)
            await self._record_call(tool_name, arguments, context, failed, None, reason)
            return GatewayCallResult(failed.decision, failed.reason)

        if response.is_error:
            reason = "MCP tool returned an error."
            failed = PolicyResult(PolicyDecision.DENY, reason)
            await self._record_call(tool_name, arguments, context, failed, None, reason)
            return GatewayCallResult(failed.decision, failed.reason)

        data = getattr(response, "structured_content", None)
        if data is None:
            data = [getattr(item, "text", "") for item in response.content]
        if tool.output_schema is not None:
            errors = sorted(Draft202012Validator(tool.output_schema).iter_errors(data), key=str)
            if errors:
                reason = "MCP tool returned output that does not match its schema."
                failed = PolicyResult(PolicyDecision.DENY, reason)
                await self._record_call(tool_name, arguments, context, failed, None, reason)
                return GatewayCallResult(failed.decision, failed.reason)

        safe_data = redact_sensitive(data)
        bounded_data, serialized = _bounded_json(safe_data, policy.max_result_bytes)
        result_hash = hashlib.sha256(serialized.encode("utf-8")).hexdigest()
        evidence_id = await self._record_call(
            tool_name,
            arguments,
            context,
            policy_result,
            result_hash,
            None,
            evidence=bounded_data,
        )
        untrusted_data = f"<untrusted_data>\n{serialized}\n</untrusted_data>"
        return GatewayCallResult(
            policy_result.decision,
            "Tool call completed.",
            evidence_id=evidence_id,
            data=bounded_data,
            untrusted_data=untrusted_data,
        )

    async def _record_call(
        self,
        tool_name: str,
        arguments: Mapping[str, Any],
        context: GatewayContext,
        result: PolicyResult,
        result_sha256: str | None,
        error: str | None,
        *,
        evidence: Any = None,
    ) -> UUID | None:
        integration_kind = _tool_integration_kind(tool_name)
        integration_id = (
            context.integration_ids.get(integration_kind) if integration_kind is not None else None
        )
        policy = _TOOL_POLICIES.get(tool_name)
        call_id = uuid7()
        evidence_id: UUID | None = None
        safe_arguments = redact_sensitive(dict(arguments))
        async with self._session_factory() as db:
            db.add(
                ToolCall(
                    id=call_id,
                    organization_id=context.organization_id,
                    investigation_id=context.investigation_id,
                    actor_id=context.actor_id,
                    integration_id=integration_id,
                    tool_name=tool_name,
                    risk=policy.risk.value if policy else "UNKNOWN",
                    decision=result.decision.value,
                    arguments=safe_arguments,
                    result_sha256=result_sha256,
                    error=redact_sensitive(error) if error else None,
                )
            )
            if evidence is not None:
                await db.flush()
                evidence_id = uuid7()
                db.add(
                    Evidence(
                        id=evidence_id,
                        organization_id=context.organization_id,
                        investigation_id=context.investigation_id,
                        tool_call_id=call_id,
                        kind=tool_name,
                        content=evidence,
                        content_sha256=result_sha256 or "",
                    )
                )
            await db.commit()
        return evidence_id
