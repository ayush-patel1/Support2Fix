import uuid
from types import SimpleNamespace
from typing import Any

import pytest
from mcp.shared.exceptions import MCPError

from app.mcp.gateway import (
    ApprovalGrant,
    GatewayContext,
    PolicyDecision,
    ToolGateway,
    canonical_arguments_sha256,
    evaluate_tool_policy,
    validate_and_inject_arguments,
)
from app.models.integration import IntegrationKind
from app.models.membership import Role


class FakeSession:
    def __init__(self) -> None:
        self.records: list[Any] = []
        self.flush_count = 0

    async def __aenter__(self) -> "FakeSession":
        return self

    async def __aexit__(self, *_args: object) -> None:
        return None

    def add(self, record: Any) -> None:
        self.records.append(record)

    async def flush(self) -> None:
        self.flush_count += 1

    async def commit(self) -> None:
        return None


class FakeSessionFactory:
    def __init__(self) -> None:
        self.session = FakeSession()

    def __call__(self) -> FakeSession:
        return self.session


class FakeMCPClient:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, object]]] = []
        self.error: Exception | None = None
        self.tools = [
            SimpleNamespace(
                name="code.search_code",
                description="Search files",
                input_schema={
                    "type": "object",
                    "properties": {
                        "organization_id": {"type": "string"},
                        "integration_id": {"type": "string"},
                        "query": {"type": "string"},
                    },
                    "required": ["organization_id", "integration_id", "query"],
                    "additionalProperties": False,
                },
                output_schema=None,
            ),
            SimpleNamespace(
                name="code.create_branch",
                description="Create branch",
                input_schema={
                    "type": "object",
                    "properties": {
                        "organization_id": {"type": "string"},
                        "integration_id": {"type": "string"},
                        "name": {"type": "string"},
                        "base": {"type": "string"},
                    },
                    "required": ["organization_id", "integration_id", "name", "base"],
                    "additionalProperties": False,
                },
                output_schema=None,
            ),
        ]

    async def list_tools(self) -> SimpleNamespace:
        return SimpleNamespace(tools=self.tools)

    async def call_tool(self, name: str, arguments: dict[str, object]) -> SimpleNamespace:
        self.calls.append((name, arguments))
        if self.error is not None:
            raise self.error
        return SimpleNamespace(
            is_error=False,
            structured_content={
                "message": "Contact admin@example.com",
                "token": "secret-value",
            },
            content=[],
        )


@pytest.fixture
def gateway_context():
    return GatewayContext(
        organization_id=uuid.uuid4(),
        actor_id=uuid.uuid4(),
        actor_role=Role.ENGINEER,
        integration_ids={
            IntegrationKind.CODE_HOST: uuid.uuid4(),
            IntegrationKind.LOG_SOURCE: uuid.uuid4(),
        },
        allowed_tools=frozenset(
            {"code.search_code", "code.create_branch", "code.create_pull_request"}
        ),
        validated_artifact_sha256="validated-diff-hash",
    )


def test_argument_validation_replaces_untrusted_tenant_scope(gateway_context):
    schema = {
        "type": "object",
        "properties": {
            "organization_id": {"type": "string", "format": "uuid"},
            "integration_id": {"type": "string", "format": "uuid"},
            "query": {"type": "string"},
        },
        "required": ["organization_id", "integration_id", "query"],
        "additionalProperties": False,
    }

    result = validate_and_inject_arguments(
        "code.search_code",
        {
            "organization_id": str(uuid.uuid4()),
            "integration_id": str(uuid.uuid4()),
            "query": "coupon",
        },
        schema,
        gateway_context,
    )

    assert result == {
        "organization_id": str(gateway_context.organization_id),
        "integration_id": str(gateway_context.integration_ids[IntegrationKind.CODE_HOST]),
        "query": "coupon",
    }


def test_argument_validation_rejects_unknown_fields(gateway_context):
    schema = {
        "type": "object",
        "properties": {"query": {"type": "string"}},
        "required": ["query"],
        "additionalProperties": False,
    }

    with pytest.raises(ValueError, match="Unknown tool argument"):
        validate_and_inject_arguments(
            "code.search_code", {"query": "coupon", "extra": True}, schema, gateway_context
        )


def test_read_tool_requires_node_capability(gateway_context):
    context = GatewayContext(
        organization_id=gateway_context.organization_id,
        actor_id=gateway_context.actor_id,
        actor_role=Role.ENGINEER,
        integration_ids=gateway_context.integration_ids,
        allowed_tools=frozenset(),
    )

    result = evaluate_tool_policy("code.search_code", {}, context)

    assert result.decision is PolicyDecision.DENY


def test_medium_tool_requires_argument_bound_approval(gateway_context):
    arguments = {"name": "support2fix/fix", "base": "main"}
    approval = ApprovalGrant(
        tool_name="code.create_branch",
        approver_role=Role.ADMIN,
        arguments_sha256=canonical_arguments_sha256(arguments),
    )

    assert evaluate_tool_policy("code.create_branch", arguments, gateway_context).decision == (
        PolicyDecision.REQUIRE_APPROVAL
    )
    assert evaluate_tool_policy(
        "code.create_branch", arguments, gateway_context, approval
    ).decision == (PolicyDecision.ALLOW)
    changed = {**arguments, "base": "production"}
    assert evaluate_tool_policy(
        "code.create_branch", changed, gateway_context, approval
    ).decision == (PolicyDecision.DENY)


def test_high_tool_requires_matching_validated_artifact(gateway_context):
    approval = ApprovalGrant(
        tool_name="code.create_pull_request",
        approver_role=Role.ENGINEER,
        artifact_sha256="different-diff-hash",
    )

    assert evaluate_tool_policy(
        "code.create_pull_request", {}, gateway_context, approval
    ).decision == (PolicyDecision.DENY)
    matching = ApprovalGrant(
        tool_name="code.create_pull_request",
        approver_role=Role.ENGINEER,
        artifact_sha256=gateway_context.validated_artifact_sha256,
    )
    assert evaluate_tool_policy(
        "code.create_pull_request", {}, gateway_context, matching
    ).decision == (PolicyDecision.ALLOW)


async def test_catalog_hides_tenant_arguments_and_unavailable_tools(gateway_context):
    context = GatewayContext(
        organization_id=gateway_context.organization_id,
        actor_id=gateway_context.actor_id,
        actor_role=Role.ENGINEER,
        integration_ids=gateway_context.integration_ids,
        allowed_tools=frozenset({"code.search_code"}),
    )
    client = FakeMCPClient()
    gateway = ToolGateway(client, FakeSessionFactory())

    tools = await gateway.list_tools(context)

    assert [tool["name"] for tool in tools] == ["code.search_code"]
    assert set(tools[0]["input_schema"]["properties"]) == {"query"}
    assert tools[0]["input_schema"]["required"] == ["query"]


async def test_unapproved_medium_call_is_audited_without_mcp_execution(gateway_context):
    client = FakeMCPClient()
    session_factory = FakeSessionFactory()
    gateway = ToolGateway(client, session_factory)

    result = await gateway.call_tool(
        "code.create_branch", {"name": "s2f/fix", "base": "main"}, gateway_context
    )

    assert result.decision is PolicyDecision.REQUIRE_APPROVAL
    assert not client.calls
    assert len(session_factory.session.records) == 1
    assert session_factory.session.records[0].decision == "REQUIRE_APPROVAL"


async def test_successful_call_injects_scope_and_persists_redacted_evidence(gateway_context):
    client = FakeMCPClient()
    session_factory = FakeSessionFactory()
    gateway = ToolGateway(client, session_factory)

    result = await gateway.call_tool(
        "code.search_code",
        {
            "organization_id": str(uuid.uuid4()),
            "integration_id": str(uuid.uuid4()),
            "query": "coupon",
        },
        gateway_context,
    )

    call = client.calls[0]
    assert call[1]["organization_id"] == str(gateway_context.organization_id)
    assert call[1]["integration_id"] == str(
        gateway_context.integration_ids[IntegrationKind.CODE_HOST]
    )
    assert result.evidence_id is not None
    assert result.data == {
        "message": "Contact [REDACTED_EMAIL]",
        "token": "[REDACTED]",
    }
    assert result.untrusted_data is not None
    assert "admin@example.com" not in result.untrusted_data
    assert len(session_factory.session.records) == 2
    assert session_factory.session.flush_count == 1
    assert session_factory.session.records[1].content == result.data


async def test_failed_idempotent_call_is_retried_and_audited(gateway_context):
    client = FakeMCPClient()
    client.error = TimeoutError()
    session_factory = FakeSessionFactory()
    gateway = ToolGateway(client, session_factory)

    result = await gateway.call_tool(
        "code.search_code", {"query": "coupon"}, gateway_context
    )

    assert result.decision is PolicyDecision.DENY
    assert "2 attempt(s): TimeoutError" in result.reason
    assert len(client.calls) == 2
    assert len(session_factory.session.records) == 1
    assert session_factory.session.records[0].error == result.reason


async def test_failed_non_idempotent_call_is_not_retried(gateway_context):
    client = FakeMCPClient()
    client.error = TimeoutError()
    session_factory = FakeSessionFactory()
    gateway = ToolGateway(client, session_factory)
    arguments = {"name": "s2f/fix", "base": "main"}
    approval = ApprovalGrant(
        tool_name="code.create_branch",
        approver_role=Role.ADMIN,
        arguments_sha256=canonical_arguments_sha256(arguments),
    )

    result = await gateway.call_tool(
        "code.create_branch", arguments, gateway_context, approval
    )

    assert result.decision is PolicyDecision.DENY
    assert "1 attempt(s): TimeoutError" in result.reason
    assert len(client.calls) == 1
    assert len(session_factory.session.records) == 1


async def test_mcp_protocol_error_is_audited_without_retry(gateway_context):
    client = FakeMCPClient()
    client.error = MCPError(-32000, "protocol failure")
    session_factory = FakeSessionFactory()
    gateway = ToolGateway(client, session_factory)

    result = await gateway.call_tool(
        "code.search_code", {"query": "coupon"}, gateway_context
    )

    assert result.decision is PolicyDecision.DENY
    assert "1 attempt(s): MCPError" in result.reason
    assert len(client.calls) == 1
    assert len(session_factory.session.records) == 1
