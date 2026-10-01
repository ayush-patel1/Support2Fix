"""The five integration interfaces from system-design.md §8. Agents (and,

from Phase 7, MCP tool handlers) depend on these Protocols, never on a
vendor's SDK directly — swapping the local adapter for GitHub/CloudWatch/a
read replica later means writing a new class that satisfies the same
shape, not touching any caller.

`SupportSource` is explicitly optional per system-design.md ("an optional
inbound integration") — Support2Fix already has its own ticket system
(Phase 3); this interface is for when an *external* support tool feeds
issues in instead.
"""

from datetime import datetime
from typing import Any, Protocol

from app.integrations.types import (
    BranchRef,
    CodeSearchResult,
    CommitInfo,
    DeploymentInfo,
    FileContent,
    LogEntry,
    PullRequestInfo,
    TableSchema,
)


class CodeHost(Protocol):
    async def search_code(self, query: str, *, limit: int = 20) -> list[CodeSearchResult]: ...
    async def get_file(self, path: str, *, ref: str | None = None) -> FileContent: ...
    async def get_commit(self, sha: str) -> CommitInfo: ...
    async def list_commits(
        self, *, path: str | None = None, limit: int = 20
    ) -> list[CommitInfo]: ...
    async def create_branch(self, name: str, *, base: str = "main") -> BranchRef: ...
    async def create_pull_request(
        self, *, branch: str, base: str, title: str, description: str
    ) -> PullRequestInfo: ...


class LogSource(Protocol):
    async def search(
        self,
        query: str,
        *,
        since: datetime | None = None,
        until: datetime | None = None,
        limit: int = 100,
    ) -> list[LogEntry]: ...
    async def get_event(self, event_id: str) -> LogEntry: ...


class DataSource(Protocol):
    async def get_schema(self) -> list[TableSchema]: ...
    async def describe_table(self, table: str) -> TableSchema: ...
    async def run_readonly_query(
        self, sql: str, *, params: dict[str, Any] | None = None, limit: int = 100
    ) -> list[dict[str, Any]]: ...


class DeploymentSource(Protocol):
    async def get_deployment(self, version: str) -> DeploymentInfo: ...
    async def list_releases(self, *, limit: int = 20) -> list[DeploymentInfo]: ...
    async def get_service_version(self) -> str: ...


class SupportSource(Protocol):
    async def get_ticket(self, ticket_id: str) -> dict[str, Any]: ...
    async def get_customer(self, customer_id: str) -> dict[str, Any]: ...
