"""GitHub CodeHost adapter authenticated with short-lived installation tokens."""

from __future__ import annotations

import base64
import binascii
import posixpath
import re
import time
from collections.abc import Callable
from datetime import datetime
from urllib.parse import quote, urlparse

import httpx
import jwt

from app.integrations.types import (
    BranchRef,
    CodeSearchResult,
    CommitInfo,
    FileContent,
    PullRequestInfo,
)

_REPOSITORY_PATTERN = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
_BRANCH_PATTERN = re.compile(r"^[A-Za-z0-9._/-]+$")
_FIELD_SEP = "\x1f"


def _valid_branch_name(name: str) -> bool:
    return (
        bool(_BRANCH_PATTERN.fullmatch(name))
        and not name.startswith("/")
        and not name.endswith(("/", "."))
        and ".." not in name
        and "//" not in name
        and "@{" not in name
        and not name.endswith(".lock")
    )


class GitHubAPIError(Exception):
    def __init__(self, message: str, status_code: int | None = None) -> None:
        self.status_code = status_code
        super().__init__(message)


class GitHubAppCodeHost:
    def __init__(
        self,
        *,
        app_id: str,
        private_key: str,
        installation_id: str,
        repository: str,
        default_branch: str = "main",
        api_url: str = "https://api.github.com",
        transport_factory: Callable[[], httpx.AsyncBaseTransport] | None = None,
    ) -> None:
        if not app_id.isdigit() or not installation_id.isdigit():
            raise ValueError("GitHub App and installation IDs must be numeric.")
        if not private_key.strip():
            raise ValueError("GitHub App private key is empty.")
        if not _REPOSITORY_PATTERN.fullmatch(repository) or any(
            part in {"", ".", ".."} for part in repository.split("/")
        ):
            raise ValueError("GitHub repository must use the owner/repository format.")
        if not _valid_branch_name(default_branch):
            raise ValueError("GitHub default branch name is invalid.")
        parsed_url = urlparse(api_url)
        if (
            parsed_url.scheme != "https"
            or not parsed_url.netloc
            or parsed_url.username
            or parsed_url.password
            or parsed_url.query
            or parsed_url.fragment
        ):
            raise ValueError("GitHub API URL must use HTTPS.")
        self.app_id = app_id
        self.private_key = private_key.replace("\\n", "\n")
        self.installation_id = installation_id
        self.repository = repository
        self.default_branch = default_branch
        self.api_url = api_url.rstrip("/")
        self._transport_factory = transport_factory

    def _app_jwt(self) -> str:
        now = int(time.time())
        return str(
            jwt.encode(
                {"iat": now - 60, "exp": now + 540, "iss": self.app_id},
                self.private_key,
                algorithm="RS256",
            )
        )

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, str | int] | None = None,
        body: dict[str, object] | None = None,
    ) -> object:
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        async with httpx.AsyncClient(
            base_url=f"{self.api_url}/",
            timeout=30,
            transport=self._transport_factory() if self._transport_factory is not None else None,
            headers=headers,
        ) as client:
            installation = await client.post(
                f"app/installations/{self.installation_id}/access_tokens",
                headers={"Authorization": f"Bearer {self._app_jwt()}"},
            )
            if installation.is_error:
                raise GitHubAPIError(
                    f"GitHub App token request failed with HTTP {installation.status_code}.",
                    installation.status_code,
                )
            installation_data = installation.json()
            token = installation_data.get("token") if isinstance(installation_data, dict) else None
            if not isinstance(token, str) or not token:
                raise GitHubAPIError("GitHub App token response did not contain an access token.")

            response = await client.request(
                method,
                path.lstrip("/"),
                params=params,
                json=body,
                headers={"Authorization": f"Bearer {token}"},
            )
            if response.is_error:
                raise GitHubAPIError(
                    f"GitHub API request failed with HTTP {response.status_code}.",
                    response.status_code,
                )
            if response.status_code == 204:
                return {}
            return response.json()

    def _repo_path(self, suffix: str) -> str:
        return f"/repos/{self.repository}/{suffix.lstrip('/')}"

    @staticmethod
    def _commit_info(commit: dict[str, object], *, files: list[str] | None = None) -> CommitInfo:
        payload = commit.get("commit")
        if not isinstance(payload, dict):
            raise GitHubAPIError("GitHub returned a commit without commit metadata.")
        author = payload.get("author")
        if not isinstance(author, dict):
            author = {}
        sha = commit.get("sha")
        message = payload.get("message")
        authored_at = author.get("date")
        if (
            not isinstance(sha, str)
            or not isinstance(message, str)
            or not isinstance(authored_at, str)
        ):
            raise GitHubAPIError("GitHub returned incomplete commit metadata.")
        git_author = payload.get("author")
        user = commit.get("author")
        author_name = (
            (user.get("login") if isinstance(user, dict) else None)
            or (git_author.get("name") if isinstance(git_author, dict) else None)
            or "unknown"
        )
        author_email = git_author.get("email") if isinstance(git_author, dict) else None
        return CommitInfo(
            sha=sha,
            message=message,
            author_name=str(author_name),
            author_email=str(author_email or ""),
            authored_at=datetime.fromisoformat(authored_at.replace("Z", "+00:00")),
            files_changed=files or [],
        )

    async def search_code(self, query: str, *, limit: int = 20) -> list[CodeSearchResult]:
        if not query.strip() or limit <= 0:
            return []
        bounded_limit = max(1, min(limit, 50))
        response = await self._request(
            "GET",
            "/search/code",
            params={
                "q": f"{query} repo:{self.repository}",
                "per_page": bounded_limit,
            },
        )
        items = response.get("items") if isinstance(response, dict) else None
        if not isinstance(items, list):
            raise GitHubAPIError("GitHub code-search response has no items list.")
        results: list[CodeSearchResult] = []
        for item in items[:bounded_limit]:
            if not isinstance(item, dict) or not isinstance(item.get("path"), str):
                continue
            file_content = await self.get_file(item["path"])
            for line_number, line in enumerate(file_content.content.splitlines(), start=1):
                if query.casefold() in line.casefold():
                    results.append(
                        CodeSearchResult(path=item["path"], line_number=line_number, line=line)
                    )
                    if len(results) >= bounded_limit:
                        return results
        return results

    async def get_file(self, path: str, *, ref: str | None = None) -> FileContent:
        if (
            not path
            or path.startswith("/")
            or ".." in path.split("/")
            or posixpath.normpath(path) != path
        ):
            raise ValueError("Repository paths must stay inside the configured repository.")
        encoded_path = quote(path, safe="/")
        response = await self._request(
            "GET",
            self._repo_path(f"contents/{encoded_path}"),
            params={"ref": ref or self.default_branch},
        )
        if not isinstance(response, dict):
            raise GitHubAPIError("GitHub file response is malformed.")
        content = response.get("content")
        encoding = response.get("encoding")
        resolved_path = response.get("path")
        resolved_ref = response.get("sha")
        if not isinstance(content, str) or encoding != "base64":
            raise GitHubAPIError("GitHub file is not available as base64 content.")
        try:
            decoded = base64.b64decode(content, validate=False).decode("utf-8")
        except (binascii.Error, UnicodeDecodeError) as exc:
            raise GitHubAPIError("GitHub file content is not valid UTF-8 base64.") from exc
        return FileContent(
            path=str(resolved_path or path),
            content=decoded,
            ref=str(resolved_ref or ref or self.default_branch),
        )

    async def get_commit(self, sha: str) -> CommitInfo:
        response = await self._request("GET", self._repo_path(f"commits/{quote(sha, safe='')}"))
        if not isinstance(response, dict):
            raise GitHubAPIError("GitHub commit response is malformed.")
        files = response.get("files", [])
        changed = (
            [
                item["filename"]
                for item in files
                if isinstance(item, dict) and isinstance(item.get("filename"), str)
            ]
            if isinstance(files, list)
            else []
        )
        return self._commit_info(response, files=changed)

    async def list_commits(self, *, path: str | None = None, limit: int = 20) -> list[CommitInfo]:
        params: dict[str, str | int] = {"per_page": max(1, min(limit, 100))}
        if path:
            params["path"] = path
        response = await self._request("GET", self._repo_path("commits"), params=params)
        if not isinstance(response, list):
            raise GitHubAPIError("GitHub commits response is malformed.")
        return [self._commit_info(item) for item in response if isinstance(item, dict)]

    async def create_branch(self, name: str, *, base: str = "main") -> BranchRef:
        if not name.startswith("support2fix/") or not _valid_branch_name(name):
            raise ValueError("New branches must use a safe support2fix/ prefix.")
        base_info = await self._request("GET", self._repo_path(f"branches/{quote(base, safe='')}"))
        if not isinstance(base_info, dict):
            raise GitHubAPIError("GitHub base branch response is malformed.")
        commit = base_info.get("commit")
        sha = commit.get("sha") if isinstance(commit, dict) else None
        if not isinstance(sha, str):
            raise GitHubAPIError("GitHub base branch has no commit SHA.")
        try:
            await self._request(
                "POST",
                self._repo_path("git/refs"),
                body={"ref": f"refs/heads/{name}", "sha": sha},
            )
        except GitHubAPIError as exc:
            if exc.status_code != 422:
                raise
            existing = await self._request(
                "GET", self._repo_path(f"git/ref/heads/{quote(name, safe='/')}")
            )
            existing_object = existing.get("object") if isinstance(existing, dict) else None
            existing_sha = existing_object.get("sha") if isinstance(existing_object, dict) else None
            if not isinstance(existing_sha, str):
                raise
            return BranchRef(name=name, base=base, head_sha=existing_sha)
        return BranchRef(name=name, base=base, head_sha=sha)

    async def create_pull_request(
        self, *, branch: str, base: str, title: str, description: str
    ) -> PullRequestInfo:
        if not branch.startswith("support2fix/") or not _valid_branch_name(branch):
            raise ValueError("Pull requests must use a support2fix/ branch.")
        existing = await self._request(
            "GET",
            self._repo_path("pulls"),
            params={
                "state": "open",
                "head": f"{self.repository.split('/')[0]}:{branch}",
                "base": base,
            },
        )
        if isinstance(existing, list) and existing:
            first = existing[0]
            if isinstance(first, dict):
                return self._pull_request(first, branch)
        response = await self._request(
            "POST",
            self._repo_path("pulls"),
            body={"head": branch, "base": base, "title": title, "body": description},
        )
        if not isinstance(response, dict):
            raise GitHubAPIError("GitHub pull-request response is malformed.")
        return self._pull_request(response, branch)

    @staticmethod
    def _pull_request(data: dict[str, object], branch: str) -> PullRequestInfo:
        number, url, title = data.get("number"), data.get("html_url"), data.get("title")
        if not isinstance(number, int) or not isinstance(url, str) or not isinstance(title, str):
            raise GitHubAPIError("GitHub returned incomplete pull-request metadata.")
        return PullRequestInfo(number=number, url=url, branch=branch, title=title)
