import uuid

from app.integrations.local.code_host import LocalGitCodeHost
from app.models.integration import Integration, IntegrationKind
from app.worker.investigations import _candidate, _error_signatures, _select_code_host


def test_hypothesis_requires_same_signature_in_logs_and_source():
    log_id = uuid.uuid4()
    code_id = uuid.uuid4()

    result = _candidate(
        "PaymentRetryExhausted",
        [
            {
                "path": "app/payment.py",
                "line_number": 42,
                "line": "raise PaymentRetryExhausted('retries reached')",
            }
        ],
        log_id,
        code_id,
    )

    assert result is not None
    assert result["classification"] == "HYPOTHESIS"
    assert result["signature"] == "PaymentRetryExhausted"
    assert result["evidence_ids"] == [str(log_id), str(code_id)]
    assert "not a confirmed root cause" in result["summary"]


def test_unrelated_code_does_not_become_a_root_cause_hypothesis():
    result = _candidate(
        "PaymentRetryExhausted",
        [{"path": "app/payment.py", "line_number": 1, "line": "return None"}],
        uuid.uuid4(),
        uuid.uuid4(),
    )

    assert result is None


def test_error_signatures_include_generic_codes_and_are_deduplicated_and_bounded():
    entries = [
        {
            "level": "ERROR",
            "message": (
                "PAY-1042 failed with PaymentRetryExhausted and payment_timeout; "
                "retrying PAY-1042. "
                "DB_CONN-7 and CACHE-12 also failed."
            ),
        },
        {"level": "INFO", "message": "IGNORED-200"},
    ]

    assert _error_signatures(entries, limit=3) == [
        "PaymentRetryExhausted",
        "payment_timeout",
        "PAY-1042",
    ]


def test_hypothesis_can_match_a_non_exception_error_code():
    log_id = uuid.uuid4()
    code_id = uuid.uuid4()

    result = _candidate(
        "PAY-1042",
        [{"path": "payments/handler.py", "line_number": 27, "line": 'raise Error("PAY-1042")'}],
        log_id,
        code_id,
    )

    assert result is not None
    assert result["signature"] == "PAY-1042"
    assert result["evidence_ids"] == [str(log_id), str(code_id)]


def test_code_host_selection_requires_ticket_association_when_multiple_repositories_exist():
    selected_id = uuid.uuid4()
    integrations = [
        Integration(id=selected_id, kind=IntegrationKind.CODE_HOST),
        Integration(id=uuid.uuid4(), kind=IntegrationKind.CODE_HOST),
    ]

    selected, gap = _select_code_host(integrations, None)

    assert selected is None
    assert gap == "Multiple code-host integrations are configured; select one on the ticket."


def test_code_host_selection_uses_ticket_association():
    selected_id = uuid.uuid4()
    integrations = [
        Integration(id=selected_id, kind=IntegrationKind.CODE_HOST),
        Integration(id=uuid.uuid4(), kind=IntegrationKind.CODE_HOST),
    ]

    selected, gap = _select_code_host(integrations, selected_id)

    assert selected is integrations[0]
    assert gap is None


def test_code_host_selection_falls_back_only_when_one_repository_exists():
    integration = Integration(id=uuid.uuid4(), kind=IntegrationKind.CODE_HOST)

    selected, gap = _select_code_host([integration], None)

    assert selected is integration
    assert gap is None


async def test_local_git_adapter_scopes_search_to_configured_subdirectory(tmp_path):
    import subprocess

    repository = tmp_path / "repository"
    shopmock = repository / "examples" / "shopmock"
    shopmock.mkdir(parents=True)
    (repository / "outside.py").write_text("PaymentRetryExhausted\n", encoding="utf-8")
    (shopmock / "payment.py").write_text("raise PaymentRetryExhausted()\n", encoding="utf-8")
    subprocess.run(["git", "init", "-q", str(repository)], check=True)
    subprocess.run(["git", "-C", str(repository), "add", "."], check=True)
    subprocess.run(
        [
            "git",
            "-C",
            str(repository),
            "-c",
            "user.email=demo@example.test",
            "-c",
            "user.name=Demo",
            "commit",
            "-q",
            "-m",
            "seed",
        ],
        check=True,
    )
    code_host = LocalGitCodeHost(str(shopmock))

    matches = await code_host.search_code("PaymentRetryExhausted")

    assert [match.path for match in matches] == ["payment.py"]
    assert (await code_host.get_file("payment.py")).content == (
        "raise PaymentRetryExhausted()\n"
    )
    try:
        await code_host.get_file("../outside.py")
    except ValueError as exc:
        assert "inside the configured directory" in str(exc)
    else:
        raise AssertionError("Repository path traversal was accepted.")
