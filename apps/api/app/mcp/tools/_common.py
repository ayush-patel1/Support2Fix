"""Shared plumbing for every tool module: resolve `(organization_id,

integration_id)` into a live adapter, scoped to this call only, and
translate the failure modes Phase 6's adapters are documented to raise
(not found, bad config, a bad git/SQL command, a local-adapter gap like
`create_pull_request`) into `ToolError` — an *anticipated* failure whose
message reaches the caller, per mcp.server.mcpserver.exceptions.ToolError.
Anything else is a real crash and is deliberately left to propagate as one.
"""

import uuid
from collections.abc import AsyncIterator, Sequence
from contextlib import asynccontextmanager
from dataclasses import asdict, is_dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Any, cast

from mcp.server.mcpserver import Context
from mcp.server.mcpserver.exceptions import ToolError
from sqlalchemy.exc import SQLAlchemyError

from app.core.errors import NotFoundError
from app.integrations.base import CodeHost, DataSource, DeploymentSource, LogSource, SupportSource
from app.integrations.local.code_host import GitCommandError
from app.integrations.registry import build_adapter
from app.mcp.context import AppContext
from app.models.integration import IntegrationKind
from app.repositories.integrations import IntegrationRepository

_ANTICIPATED_ERRORS: tuple[type[Exception], ...] = (
    NotFoundError,
    ValueError,
    GitCommandError,
    NotImplementedError,
    SQLAlchemyError,
)

Adapter = CodeHost | LogSource | DataSource | DeploymentSource | SupportSource


@asynccontextmanager
async def tool_adapter(
    ctx: Context, *, organization_id: str, integration_id: str, expected_kind: IntegrationKind
) -> AsyncIterator[Adapter]:
    """Resolves the Integration and builds its adapter, scoped to this call.

    Yields the `Adapter` union — each tool module's own `_adapter()` helper
    casts it to the one concrete Protocol its integration kind satisfies,
    since that mapping is a fact about `IntegrationKind`/`registry.py` this
    module doesn't need to know.
    """
    app_ctx = cast(AppContext, ctx.request_context.lifespan_context)
    try:
        async with app_ctx.session_factory() as db:
            integration = await IntegrationRepository(db).get(
                uuid.UUID(organization_id), uuid.UUID(integration_id)
            )
            if integration is None:
                raise NotFoundError(f"Integration {integration_id} not found.")
            if integration.kind != expected_kind:
                raise ValueError(
                    f"Integration {integration_id} is kind={integration.kind.value}, "
                    f"expected {expected_kind.value}."
                )
            adapter = build_adapter(integration, db=db)
            try:
                yield adapter
            finally:
                aclose = getattr(adapter, "aclose", None)
                if aclose is not None:
                    await aclose()
    except _ANTICIPATED_ERRORS as exc:
        raise ToolError(str(exc)) from exc


def to_jsonable(value: Any) -> Any:
    """Recursively converts a Phase 6 adapter result into plain JSON types.

    Covers the shapes those adapters actually return: frozen dataclasses
    (app/integrations/types.py), lists of them, and `dict[str, Any]` rows
    from `run_readonly_query` against an arbitrary customer table (hence
    the `date`/`Decimal` cases, not just `datetime`).
    """
    if is_dataclass(value) and not isinstance(value, type):
        return to_jsonable(asdict(value))
    if isinstance(value, dict):
        return {k: to_jsonable(v) for k, v in value.items()}
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        return [to_jsonable(v) for v in value]
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, uuid.UUID):
        return str(value)
    return value
