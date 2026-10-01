"""Vendor-neutral return types shared by every integration interface. An

adapter for a real vendor (GitHub, CloudWatch, ...) maps that vendor's own
response shape onto these — callers (and, later, MCP tool schemas in
Phase 7) never see vendor-specific fields.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class CodeSearchResult:
    path: str
    line_number: int
    line: str


@dataclass(frozen=True)
class CommitInfo:
    sha: str
    message: str
    author_name: str
    author_email: str
    authored_at: datetime
    files_changed: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class FileContent:
    path: str
    content: str
    ref: str


@dataclass(frozen=True)
class BranchRef:
    name: str
    base: str
    head_sha: str


@dataclass(frozen=True)
class PullRequestInfo:
    number: int
    url: str
    branch: str
    title: str


@dataclass(frozen=True)
class LogEntry:
    id: str
    timestamp: datetime
    level: str
    service: str
    message: str
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ColumnInfo:
    name: str
    data_type: str
    nullable: bool


@dataclass(frozen=True)
class TableSchema:
    name: str
    columns: list[ColumnInfo]


@dataclass(frozen=True)
class DeploymentInfo:
    service: str
    version: str
    commit_sha: str | None
    deployed_at: datetime
    status: str
