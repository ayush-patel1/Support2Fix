"""Factory mapping an `Integration` DB record to a concrete adapter

instance satisfying the matching Protocol from base.py. This is the one
place that knows every (kind, provider) pair that exists — callers
(services, and from Phase 7 the MCP tool layer) ask for an adapter by
Integration record and never import a concrete `local.*` class themselves.

Adding a real vendor adapter later (e.g. GitHub for `CodeHost`) means
adding one branch here, not touching any caller.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.base import CodeHost, DataSource, DeploymentSource, LogSource, SupportSource
from app.integrations.local.code_host import LocalGitCodeHost
from app.integrations.local.data_source import LocalPostgresDataSource
from app.integrations.local.deployment_source import LocalFileDeploymentSource
from app.integrations.local.log_source import LocalFileLogSource
from app.integrations.local.support_source import LocalTicketSupportSource
from app.models.integration import Integration, IntegrationKind, IntegrationProvider


def _require_config_str(integration: Integration, key: str) -> str:
    value = integration.config.get(key)
    if not isinstance(value, str) or not value:
        raise ValueError(
            f"Integration {integration.id} (kind={integration.kind.value}) is missing a "
            f"non-empty {key!r} string in its config."
        )
    return value


def build_adapter(
    integration: Integration, *, db: AsyncSession | None = None
) -> CodeHost | LogSource | DataSource | DeploymentSource | SupportSource:
    """Build the adapter this Integration record describes.

    `db` is only required for `SUPPORT_SOURCE`, the one kind that wraps the
    platform's own database instead of an external system.
    """
    if integration.provider != IntegrationProvider.LOCAL:
        raise ValueError(
            f"No adapter registered for provider {integration.provider.value!r} "
            f"(kind={integration.kind.value})."
        )

    if integration.kind == IntegrationKind.CODE_HOST:
        return LocalGitCodeHost(_require_config_str(integration, "repo_path"))

    if integration.kind == IntegrationKind.LOG_SOURCE:
        return LocalFileLogSource(_require_config_str(integration, "log_path"))

    if integration.kind == IntegrationKind.DATA_SOURCE:
        return LocalPostgresDataSource(_require_config_str(integration, "database_url"))

    if integration.kind == IntegrationKind.DEPLOYMENT_SOURCE:
        return LocalFileDeploymentSource(_require_config_str(integration, "deployments_path"))

    if integration.kind == IntegrationKind.SUPPORT_SOURCE:
        if db is None:
            raise ValueError("SUPPORT_SOURCE requires a database session.")
        return LocalTicketSupportSource(db, integration.organization_id)

    raise AssertionError(f"Unhandled integration kind: {integration.kind!r}")
