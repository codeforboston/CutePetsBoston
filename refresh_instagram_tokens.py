"""Renew Instagram Login tokens without publishing or logging credentials."""

import os
import subprocess
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import requests

from social_posters.instagram import GRAPH_API_BASE

REFRESH_URL = "https://graph.instagram.com/refresh_access_token"
ATTEMPTS = 3
ACCOUNTS = (
    ("Production", "INSTAGRAM_PAGE_ACCESS_TOKEN", "INSTAGRAM_BUSINESS_ACCOUNT_ID"),
    ("Test", "INSTAGRAM_TEST_PAGE_ACCESS_TOKEN", "INSTAGRAM_TEST_BUSINESS_ACCOUNT_ID"),
)


class RefreshError(Exception):
    """An error whose message is safe for workflow logs."""


def mask_token(token: str) -> None:
    if os.environ.get("GITHUB_ACTIONS") == "true":
        escaped = token.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")
        print(f"::add-mask::{escaped}", flush=True)


def meta_get(url: str, *, params: dict[str, str], token: str | None = None) -> dict[str, Any]:
    """Retry transient failures; never expose requests' credential-bearing errors."""
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    for attempt in range(ATTEMPTS):
        try:
            response = requests.get(url, params=params, headers=headers, timeout=30, allow_redirects=False)
        except requests.Timeout, requests.ConnectionError:
            if attempt == ATTEMPTS - 1:
                raise RefreshError("Meta request timed out or could not connect; retry the workflow.") from None
        except requests.RequestException:
            raise RefreshError("Meta request failed; check account authorization and retry.") from None
        else:
            if response.status_code == 429 or 500 <= response.status_code < 600:
                if attempt == ATTEMPTS - 1:
                    raise RefreshError(f"Meta unavailable after retries (HTTP {response.status_code}).")
            elif response.status_code != 200:
                raise RefreshError(
                    f"Meta rejected the request (HTTP {response.status_code}); check token eligibility and authorization."
                )
            else:
                try:
                    payload = response.json()
                except ValueError:
                    raise RefreshError("Meta returned invalid JSON.") from None
                if not isinstance(payload, dict):
                    raise RefreshError("Meta returned an invalid response.")
                returned_token = payload.get("access_token")
                if isinstance(returned_token, str) and returned_token:
                    mask_token(returned_token)
                if "error" in payload:
                    raise RefreshError("Meta rejected the request; check token eligibility and authorization.")
                return payload
        time.sleep(2 ** (attempt + 1))
    raise RefreshError("Meta request failed.")


def save_secret(repository: str, name: str, token: str) -> None:
    """gh encrypts stdin locally; suppress CLI output, including errors."""
    for attempt in range(ATTEMPTS):
        try:
            subprocess.run(
                ["gh", "secret", "set", name, "--repo", repository, "--app", "actions"],
                input=token,
                text=True,
                capture_output=True,
                check=True,
                timeout=45,
            )
            return
        except subprocess.SubprocessError, OSError:
            if attempt == ATTEMPTS - 1:
                raise RefreshError(
                    "GitHub secret update failed; check the App's Secrets write access and retry."
                ) from None
        time.sleep(2 ** (attempt + 1))


def refresh_account(repository: str, secret_name: str, account_variable: str) -> datetime:
    token = os.environ.get(secret_name, "")
    account_id = os.environ.get(account_variable, "")
    if not token or not account_id:
        raise RefreshError("Missing account ID or Instagram token; configure both repository secrets.")
    mask_token(token)
    # Start the expiration estimate before the request to avoid overstating its lifetime.
    started = datetime.now(timezone.utc)
    payload = meta_get(REFRESH_URL, params={"grant_type": "ig_refresh_token", "access_token": token})
    renewed_token = payload.get("access_token")
    expires_in = payload.get("expires_in")
    if not isinstance(renewed_token, str) or not renewed_token.strip() or any(c.isspace() for c in renewed_token):
        raise RefreshError("Meta did not return a usable token; existing secret was not changed.")
    if type(expires_in) is not int or expires_in <= 0:
        raise RefreshError("Meta did not return a positive integer expires_in; existing secret was not changed.")
    try:
        expires_at = started + timedelta(seconds=expires_in)
    except OverflowError:
        raise RefreshError("Meta returned an invalid expiration; existing secret was not changed.") from None
    account = meta_get(f"{GRAPH_API_BASE}/me", params={"fields": "id,username"}, token=renewed_token)
    if (
        str(account.get("id", "")) != account_id
        or not isinstance(account.get("username"), str)
        or not account["username"]
    ):
        raise RefreshError(
            "Renewed token did not match the configured Instagram account; existing secret was not changed."
        )
    save_secret(repository, secret_name, renewed_token)
    return expires_at


def main() -> int:
    repository = os.environ.get("GITHUB_REPOSITORY", "")
    if not repository or not os.environ.get("GH_TOKEN"):
        print("Missing GITHUB_REPOSITORY or GH_TOKEN; no tokens were refreshed.")
        return 1
    results = ["## Instagram token refresh", ""]
    failed = False
    for label, secret_name, account_variable in ACCOUNTS:
        try:
            expires_at = refresh_account(repository, secret_name, account_variable)
            result = f"{label}: refreshed, validated, and saved. Estimated expiry: {expires_at.isoformat()}."
        except RefreshError as exc:
            failed = True
            result = f"{label}: FAILED. {exc}"
        except Exception:
            # Avoid traceback/exception text: HTTP errors can embed token-bearing URLs.
            failed = True
            result = f"{label}: FAILED. Unexpected maintenance error; inspect configuration and retry."
        print(result)
        results.append(f"- {result}")
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_path:
        with Path(summary_path).open("a", encoding="utf-8") as summary:
            summary.write("\n".join(results) + "\n")
    return int(failed)


if __name__ == "__main__":
    raise SystemExit(main())
