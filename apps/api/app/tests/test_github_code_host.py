import base64
import json
import uuid

import httpx
import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from app.core.config import get_settings
from app.integrations.github.code_host import GitHubAppCodeHost
from app.integrations.registry import build_adapter
from app.models.integration import Integration, IntegrationKind, IntegrationProvider


@pytest.fixture
def github_host_and_requests():
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()
    public_key = private_key.public_key()
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.url.path == "/app/installations/12345/access_tokens":
            token = request.headers.get("Authorization", "").removeprefix("Bearer ")
            claims = jwt.decode(token, public_key, algorithms=["RS256"])
            assert claims["iss"] == "67890"
            return httpx.Response(201, json={"token": "installation-token"})
        if request.url.path == "/search/code":
            return httpx.Response(200, json={"items": [{"path": "src/payments.py"}]})
        if request.url.path == "/repos/acme/payments/contents/src/payments.py":
            return httpx.Response(
                200,
                json={
                    "path": "src/payments.py",
                    "sha": "commit-sha",
                    "encoding": "base64",
                    "content": base64.b64encode(
                        b"raise PaymentRetryExhausted('retry limit')\n"
                    ).decode(),
                },
            )
        if request.url.path == "/repos/acme/payments/branches/main":
            return httpx.Response(200, json={"commit": {"sha": "base-sha"}})
        if request.url.path == "/repos/acme/payments/git/refs":
            assert json.loads(request.content) == {
                "ref": "refs/heads/support2fix/issue-123",
                "sha": "base-sha",
            }
            return httpx.Response(201, json={})
        if request.url.path == "/repos/acme/payments/pulls" and request.method == "GET":
            return httpx.Response(200, json=[])
        if request.url.path == "/repos/acme/payments/pulls" and request.method == "POST":
            return httpx.Response(
                201,
                json={
                    "number": 17,
                    "html_url": "https://github.com/acme/payments/pull/17",
                    "title": "Fix payment retry",
                },
            )
        return httpx.Response(404, json={"message": "Not found"})

    host = GitHubAppCodeHost(
        app_id="67890",
        private_key=private_pem,
        installation_id="12345",
        repository="acme/payments",
        default_branch="main",
        transport_factory=lambda: httpx.MockTransport(handler),
    )
    return host, requests


async def test_github_app_reads_search_results_and_creates_scoped_branch_and_pr(
    github_host_and_requests,
):
    host, requests = github_host_and_requests

    matches = await host.search_code("PaymentRetryExhausted")
    branch = await host.create_branch("support2fix/issue-123")
    pull_request = await host.create_pull_request(
        branch=branch.name,
        base="main",
        title="Fix payment retry",
        description="Evidence-backed candidate fix.",
    )

    assert [(match.path, match.line_number) for match in matches] == [("src/payments.py", 1)]
    assert branch.head_sha == "base-sha"
    assert pull_request.number == 17
    assert pull_request.url == "https://github.com/acme/payments/pull/17"
    api_requests = [
        request
        for request in requests
        if request.url.path != "/app/installations/12345/access_tokens"
    ]
    assert all(
        request.headers["Authorization"] == "Bearer installation-token" for request in api_requests
    )


async def test_github_app_rejects_unsafe_repository_and_branch():
    with pytest.raises(ValueError, match="owner/repository"):
        GitHubAppCodeHost(
            app_id="1",
            private_key="not-validated-until-use",
            installation_id="2",
            repository="../untrusted",
        )

    host = GitHubAppCodeHost(
        app_id="1",
        private_key="not-validated-until-use",
        installation_id="2",
        repository="acme/payments",
    )
    with pytest.raises(ValueError, match="support2fix/"):
        await host.create_branch("main")


def test_integration_registry_builds_github_app_adapter(monkeypatch):
    monkeypatch.setenv("GITHUB_APP_ID", "67890")
    monkeypatch.setenv("GITHUB_APP_PRIVATE_KEY", "test-key")
    get_settings.cache_clear()
    try:
        integration = Integration(
            id=uuid.uuid4(),
            organization_id=uuid.uuid4(),
            kind=IntegrationKind.CODE_HOST,
            provider=IntegrationProvider.GITHUB_APP,
            name="payments",
            config={
                "installation_id": "12345",
                "repository": "acme/payments",
                "default_branch": "trunk",
            },
        )

        adapter = build_adapter(integration)

        assert isinstance(adapter, GitHubAppCodeHost)
        assert adapter.default_branch == "trunk"
    finally:
        get_settings.cache_clear()
