"""Exercise the real CLI against comments from a second owned Mastodon account."""

import json
import os
import subprocess
import sys
import time
from pathlib import Path

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from reply_inbox import save_json
from social_replies.adapters import MastodonReplies

ROOT_ID = "117555647985135210"
RESULT = Path("comment-reply-test-results.json")


def call(method: str, url: str, **kwargs) -> dict:
    if method == "GET":
        with requests.Session() as session:
            session.mount("https://", HTTPAdapter(max_retries=Retry(total=2, backoff_factor=1)))
            response = session.get(url, timeout=25, **kwargs)
    else:
        response = requests.request(method, url, timeout=25, **kwargs)
    response.raise_for_status()
    return response.json()


def run(report: dict) -> None:
    base = "https://mastodon.social"
    sender_token = (os.environ.get("MASTODON_TOKEN") or "").strip()
    commenter_token = (os.environ.get("COMMENTER_MASTODON_TOKEN") or "").strip()
    if not sender_token or not commenter_token:
        raise ValueError("Both owned-account tokens are required")
    sender_headers = {"Authorization": f"Bearer {sender_token}"}
    commenter_headers = {"Authorization": f"Bearer {commenter_token}"}
    sender = call("GET", f"{base}/api/v1/accounts/verify_credentials", headers=sender_headers)
    commenter = call("GET", f"{base}/api/v1/accounts/verify_credentials", headers=commenter_headers)
    root = call("GET", f"{base}/api/v1/statuses/{ROOT_ID}", headers=sender_headers)
    assert sender["id"] == root["account"]["id"]
    assert sender["id"] != commenter["id"]
    assert commenter["acct"].casefold() == "cutepetsboston"
    assert not commenter.get("bot", False), "The engine correctly excludes bot-labelled commenters"
    assert "reply-engine test" in root["content"]
    report.update(sender=sender["acct"], commenter=commenter["acct"], test_thread=root["url"])
    save_json(RESULT, report)

    fixtures = {}
    for name, text in (("question", "How can I adopt?"), ("friendly", "So cute! 🐾")):
        saved = call(
            "POST",
            f"{base}/api/v1/statuses",
            headers={**commenter_headers, "Idempotency-Key": f"comment-e2e-{os.environ['GITHUB_RUN_ID']}-{name}"},
            data={
                "status": f"@{sender['acct']} {text} (controlled reply test)",
                "in_reply_to_id": ROOT_ID,
                "visibility": "unlisted",
            },
        )
        fixtures[name] = saved
        report[name + "_comment"] = {"id": saved["id"], "url": saved["url"]}
        save_json(RESULT, report)

    database = Path("comment-reply-test-database.json")
    save_json(
        database,
        {
            "posts": [
                {
                    "pet_id": "controlled-test",
                    "platform": "Mastodon",
                    "post_id": ROOT_ID,
                    "post_url": root["url"],
                    "posted_at": root["created_at"],
                }
            ]
        },
    )
    adapter = MastodonReplies()
    post = json.loads(database.read_text())["posts"][0]
    for attempt in range(10):
        incoming = {comment.comment_id: comment for comment in adapter.read(post)}
        if all(item["id"] in incoming for item in fixtures.values()):
            break
        time.sleep(2)
    else:
        raise ValueError("Our new comments have not appeared; do not resend them")
    assert not incoming[fixtures["friendly"]["id"]].is_own
    assert incoming[fixtures["friendly"]["id"]].author_id == commenter["id"]
    # This is the real application entry point, not a direct call to its sender.
    command = [
        sys.executable,
        "reply_inbox.py",
        "--database",
        str(database),
        "--output",
        "comment-reply-preview.json",
        "--state",
        "comment-reply-state.json",
        "--rate",
        "1",
        "--daily-cap",
        "1",
        "--send",
    ]
    subprocess.run(command, check=True)
    first = json.loads(Path("comment-reply-preview.json").read_text())
    expected_key = f"Mastodon:{fixtures['friendly']['id']}"
    assert [proposal["comment"] for proposal in first["proposals"]] == [expected_key]
    assert first["results"] == [{"comment": expected_key, "success": True}]
    state = json.loads(Path("comment-reply-state.json").read_text())
    entry = state["processed"][expected_key]
    saved = call("GET", f"{base}/api/v1/statuses/{entry['reply_id']}", headers=sender_headers)
    assert saved["in_reply_to_id"] == fixtures["friendly"]["id"]
    assert saved["in_reply_to_id"] != ROOT_ID
    assert saved["account"]["id"] == sender["id"]
    report.update(
        reply_url=saved["url"],
        reply_text=entry["text"],
        replied_to_comment=True,
        friendly_selected=True,
        question_skipped=True,
    )
    save_json(RESULT, report)

    subprocess.run(command, check=True)
    second = json.loads(Path("comment-reply-preview.json").read_text())
    assert second["proposals"] == [] and second["results"] == []
    descendants = call("GET", f"{base}/api/v1/statuses/{ROOT_ID}/context", headers=sender_headers)["descendants"]
    sent = [
        item
        for item in descendants
        if item.get("in_reply_to_id") == fixtures["friendly"]["id"] and item["account"]["id"] == sender["id"]
    ]
    assert len(sent) == 1
    assert not any(
        item.get("in_reply_to_id") == fixtures["question"]["id"] and item["account"]["id"] == sender["id"]
        for item in descendants
    )
    report.update(status="passed", duplicate_skipped=True, exactly_one_reply=True)


def main() -> None:
    report: dict = {"status": "started"}
    try:
        run(report)
    except Exception as exc:
        report.update(
            status="failed",
            error=type(exc).__name__,
            note="Inspect the saved comment IDs and state before retrying; a write may have succeeded",
        )
        if isinstance(exc, requests.HTTPError) and exc.response is not None:
            report["http_status"] = exc.response.status_code
    save_json(RESULT, report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as output:
            output.write(f"Comment-to-reply test: **{report['status']}**\n\n")
            for name in ("test_thread", "reply_url"):
                if report.get(name):
                    output.write(f"[{name}]({report[name]})\n\n")
    if report["status"] != "passed":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
