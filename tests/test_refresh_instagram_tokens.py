import subprocess
from datetime import datetime, timezone
from unittest.mock import Mock

import pytest
import requests

import refresh_instagram_tokens as refresh

OLD_TOKEN = "old-private-token"
NEW_TOKEN = "renewed-private-token"


@pytest.fixture
def setup_refresh(monkeypatch, tmp_path):
    monkeypatch.setenv("GH_TOKEN", "github-private-token")
    monkeypatch.setenv("GITHUB_REPOSITORY", "owner/repo")
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(tmp_path / "summary.md"))
    for _, token_variable, account_variable in refresh.ACCOUNTS:
        monkeypatch.setenv(token_variable, OLD_TOKEN)
        monkeypatch.setenv(account_variable, "123")
    monkeypatch.setattr(refresh.time, "sleep", Mock())
    get = Mock()
    monkeypatch.setattr(refresh.requests, "get", get)
    run = Mock()
    monkeypatch.setattr(refresh.subprocess, "run", run)
    return get, run, tmp_path / "summary.md"


def response(payload=None, status=200):
    return Mock(status_code=status, json=Mock(return_value=payload))


def valid_responses():
    return [
        response({"access_token": NEW_TOKEN, "expires_in": 5184000}),
        response({"id": "123", "username": "cutepets"}),
    ]


def test_refreshes_validates_and_saves_both_accounts(setup_refresh, capsys):
    get, run, summary = setup_refresh
    get.side_effect = valid_responses() + valid_responses()
    before = datetime.now(timezone.utc)
    assert refresh.main() == 0
    assert get.call_count == 4
    assert get.call_args_list[0].kwargs == {
        "params": {"grant_type": "ig_refresh_token", "access_token": OLD_TOKEN},
        "headers": {},
        "timeout": 30,
        "allow_redirects": False,
    }
    assert get.call_args_list[1].args == (f"{refresh.GRAPH_API_BASE}/me",)
    assert get.call_args_list[1].kwargs["headers"] == {"Authorization": f"Bearer {NEW_TOKEN}"}
    for call, (_, secret_name, _) in zip(run.call_args_list, refresh.ACCOUNTS, strict=True):
        assert call.args[0] == ["gh", "secret", "set", secret_name, "--repo", "owner/repo", "--app", "actions"]
        assert call.kwargs == {"input": NEW_TOKEN, "text": True, "capture_output": True, "check": True, "timeout": 45}
    text = summary.read_text()
    assert "Production: refreshed" in text and "Test: refreshed" in text
    expiry = datetime.fromisoformat(text.split("Estimated expiry: ")[1].split(".\n")[0])
    assert 59 <= (expiry - before).days <= 60
    output = capsys.readouterr().out
    # Mask commands are consumed by Actions, not visible log messages.
    visible = "\n".join(line for line in output.splitlines() if not line.startswith("::add-mask::"))
    for token in (OLD_TOKEN, NEW_TOKEN, "github-private-token"):
        assert token not in visible and token not in text
    assert output.index(f"::add-mask::{NEW_TOKEN}") < output.index("Production: refreshed")


@pytest.mark.parametrize("status", [400, 401, 403])
def test_rejected_token_preserves_secret_and_continues_other_account(setup_refresh, status):
    get, run, summary = setup_refresh
    get.side_effect = [response({"error": {"message": OLD_TOKEN}}, status)] + valid_responses()
    assert refresh.main() == 1
    run.assert_called_once()
    assert run.call_args.args[0][3] == "INSTAGRAM_TEST_PAGE_ACCESS_TOKEN"
    assert "Production: FAILED" in summary.read_text()
    assert "Test: refreshed" in summary.read_text()


@pytest.mark.parametrize(
    "payload",
    [
        {},
        [],
        {"access_token": "", "expires_in": 30},
        {"access_token": NEW_TOKEN, "expires_in": 0},
        {"access_token": NEW_TOKEN, "expires_in": -1},
        {"access_token": NEW_TOKEN, "expires_in": True},
        {"access_token": NEW_TOKEN, "expires_in": "5184000"},
        {"access_token": NEW_TOKEN, "expires_in": 10**30},
        {"access_token": "bad\ntoken", "expires_in": 30},
        {"access_token": NEW_TOKEN, "error": {"message": NEW_TOKEN}},
    ],
)
def test_invalid_refresh_response_never_updates_secret(setup_refresh, payload):
    get, run, _ = setup_refresh
    get.return_value = response(payload)
    with pytest.raises(refresh.RefreshError):
        refresh.refresh_account("owner/repo", "INSTAGRAM_PAGE_ACCESS_TOKEN", "INSTAGRAM_BUSINESS_ACCOUNT_ID")
    run.assert_not_called()


@pytest.mark.parametrize("account", [{"id": "456", "username": "other"}, {"id": "123"}, {"error": {}}])
def test_invalid_account_preserves_secret(setup_refresh, account):
    get, run, _ = setup_refresh
    get.side_effect = [valid_responses()[0], response(account)]
    with pytest.raises(refresh.RefreshError):
        refresh.refresh_account("owner/repo", "INSTAGRAM_PAGE_ACCESS_TOKEN", "INSTAGRAM_BUSINESS_ACCOUNT_ID")
    run.assert_not_called()


@pytest.mark.parametrize("failure", [requests.Timeout(OLD_TOKEN), requests.ConnectionError(OLD_TOKEN), 429, 503])
def test_transient_errors_retry_then_succeed(setup_refresh, failure):
    get, run, _ = setup_refresh
    failed = response(status=failure) if isinstance(failure, int) else failure
    get.side_effect = [failed, failed] + valid_responses()
    refresh.refresh_account("owner/repo", "INSTAGRAM_PAGE_ACCESS_TOKEN", "INSTAGRAM_BUSINESS_ACCOUNT_ID")
    assert get.call_count == 4
    run.assert_called_once()


@pytest.mark.parametrize("failure", [requests.Timeout(OLD_TOKEN), response(status=429), response(status=503)])
def test_retry_exhaustion_preserves_secret(setup_refresh, failure):
    get, run, _ = setup_refresh
    get.side_effect = [failure] * 3
    with pytest.raises(refresh.RefreshError):
        refresh.refresh_account("owner/repo", "INSTAGRAM_PAGE_ACCESS_TOKEN", "INSTAGRAM_BUSINESS_ACCOUNT_ID")
    assert get.call_count == 3
    run.assert_not_called()


def test_secret_update_failure_is_sanitized_and_other_account_runs(setup_refresh, capsys):
    get, run, summary = setup_refresh
    get.side_effect = valid_responses() + valid_responses()
    run.side_effect = [subprocess.CalledProcessError(1, "gh", stderr=NEW_TOKEN)] * 3 + [Mock()]
    assert refresh.main() == 1
    assert run.call_count == 4
    assert "GitHub secret update failed" in summary.read_text()
    assert "Test: refreshed" in summary.read_text()
    assert NEW_TOKEN not in summary.read_text()
    assert "Traceback" not in capsys.readouterr().out


def test_invalid_json_is_sanitized(setup_refresh):
    get, run, _ = setup_refresh
    get.return_value = response()
    get.return_value.json.side_effect = ValueError(OLD_TOKEN)
    with pytest.raises(refresh.RefreshError, match="invalid JSON"):
        refresh.refresh_account("owner/repo", "INSTAGRAM_PAGE_ACCESS_TOKEN", "INSTAGRAM_BUSINESS_ACCOUNT_ID")
    run.assert_not_called()


def test_missing_account_credentials_does_not_block_other_account(setup_refresh, monkeypatch):
    get, run, _ = setup_refresh
    monkeypatch.delenv("INSTAGRAM_PAGE_ACCESS_TOKEN")
    get.side_effect = valid_responses()
    assert refresh.main() == 1
    run.assert_called_once()


def test_missing_github_credentials_fails_before_refresh(setup_refresh, monkeypatch):
    get, run, _ = setup_refresh
    monkeypatch.delenv("GH_TOKEN")
    assert refresh.main() == 1
    get.assert_not_called()
    run.assert_not_called()


def test_unexpected_errors_are_sanitized_and_do_not_block_test_account(setup_refresh):
    get, run, summary = setup_refresh
    get.side_effect = [RuntimeError(OLD_TOKEN)] + valid_responses()
    assert refresh.main() == 1
    assert OLD_TOKEN not in summary.read_text()
    run.assert_called_once()
