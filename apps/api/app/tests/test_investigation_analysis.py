import uuid

from app.integrations.local.code_host import LocalGitCodeHost
from app.worker.investigations import _candidate


def test_hypothesis_requires_same_signature_in_logs_and_source():
    log_id = uuid.uuid4()
    code_id = uuid.uuid4()

    result = _candidate(
        [{"level": "ERROR", "message": "PaymentRetryExhausted: retries reached"}],
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
        [{"level": "ERROR", "message": "PaymentRetryExhausted: retries reached"}],
        [{"path": "app/payment.py", "line_number": 1, "line": "return None"}],
        uuid.uuid4(),
        uuid.uuid4(),
    )

    assert result is None


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
