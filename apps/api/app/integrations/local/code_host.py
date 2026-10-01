"""CodeHost backed by a real local git repository — no vendor API, no

network, just `git` shelled out against a filesystem path. This is the
adapter ADR-001 D13 calls "the local git adapter" (the default; GitHub is
the real adapter, not built yet).

`create_pull_request` has no local equivalent (a PR is a hosted-platform
concept) and raises `NotImplementedError` rather than faking one — a real
implementation needs the GitHub adapter (Phase 15).
"""

import asyncio
import subprocess
from datetime import datetime
from pathlib import Path

from app.integrations.types import (
    BranchRef,
    CodeSearchResult,
    CommitInfo,
    FileContent,
    PullRequestInfo,
)

_FIELD_SEP = "\x1f"  # unit separator — won't collide with real commit content
_LOG_FORMAT = f"%H{_FIELD_SEP}%s{_FIELD_SEP}%an{_FIELD_SEP}%ae{_FIELD_SEP}%aI"


class GitCommandError(Exception):
    pass


class LocalGitCodeHost:
    def __init__(self, repo_path: str) -> None:
        self.repo_path = Path(repo_path).resolve()
        if not (self.repo_path / ".git").is_dir():
            raise ValueError(f"{self.repo_path} is not a git repository (no .git directory).")

    async def _run(self, *args: str) -> subprocess.CompletedProcess[str]:
        def run() -> subprocess.CompletedProcess[str]:
            return subprocess.run(
                ["git", *args],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )

        return await asyncio.to_thread(run)

    async def _git(self, *args: str) -> str:
        result = await self._run(*args)
        if result.returncode != 0:
            raise GitCommandError(f"git {' '.join(args)} failed: {result.stderr.strip()}")
        return result.stdout

    def _parse_commit_line(self, line: str) -> CommitInfo:
        sha, message, author_name, author_email, authored_at = line.split(_FIELD_SEP)
        return CommitInfo(
            sha=sha,
            message=message,
            author_name=author_name,
            author_email=author_email,
            authored_at=datetime.fromisoformat(authored_at),
        )

    async def search_code(self, query: str, *, limit: int = 20) -> list[CodeSearchResult]:
        result = await self._run("grep", "-n", "--fixed-strings", query, "HEAD")
        # git grep's exit code 1 means "no matches" — not an error. Only
        # treat >= 2 (a real problem: bad repo state, bad args, ...) as one.
        if result.returncode >= 2:
            raise GitCommandError(f"git grep failed: {result.stderr.strip()}")
        if result.returncode == 1:
            return []

        results = []
        for line in result.stdout.splitlines()[:limit]:
            # format: "HEAD:path/to/file.py:12:    the matching line"
            _, path, line_no, content = line.split(":", 3)
            results.append(CodeSearchResult(path=path, line_number=int(line_no), line=content))
        return results

    async def get_file(self, path: str, *, ref: str | None = None) -> FileContent:
        ref = ref or "HEAD"
        content = await self._git("show", f"{ref}:{path}")
        return FileContent(path=path, content=content, ref=ref)

    async def get_commit(self, sha: str) -> CommitInfo:
        output = await self._git("show", "--no-patch", f"--format={_LOG_FORMAT}", sha)
        commit = self._parse_commit_line(output.strip())
        files = await self._git("diff-tree", "--no-commit-id", "--name-only", "-r", sha)
        return CommitInfo(
            sha=commit.sha,
            message=commit.message,
            author_name=commit.author_name,
            author_email=commit.author_email,
            authored_at=commit.authored_at,
            files_changed=[f for f in files.splitlines() if f],
        )

    async def list_commits(self, *, path: str | None = None, limit: int = 20) -> list[CommitInfo]:
        args = ["log", f"--format={_LOG_FORMAT}", f"-n{limit}"]
        if path:
            args += ["--", path]
        output = await self._git(*args)
        return [self._parse_commit_line(line) for line in output.splitlines() if line]

    async def create_branch(self, name: str, *, base: str = "main") -> BranchRef:
        await self._git("branch", name, base)
        head_sha = (await self._git("rev-parse", name)).strip()
        return BranchRef(name=name, base=base, head_sha=head_sha)

    async def create_pull_request(
        self, *, branch: str, base: str, title: str, description: str
    ) -> PullRequestInfo:
        raise NotImplementedError(
            "The local git adapter has no pull-request concept — that needs the "
            "GitHub adapter (Phase 15), not built yet."
        )
