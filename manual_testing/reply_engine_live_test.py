"""Controlled transport/executor tests on configured test accounts only."""

import json
import os
import sys
import time
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from database import PublishedPost
from reply_inbox import save_json, send_proposals
from social_posters.instagram import GRAPH_API_BASE
from social_replies.adapters import InstagramReplies, MastodonReplies
from social_replies.engine import ReplyPolicy, pick_replies
from social_replies.models import Comment, ReplyAdapter


def request(method: str, url: str, **kwargs) -> dict:
    response = requests.request(method, url, timeout=25, **kwargs)
    response.raise_for_status()
    return response.json()


def exercise(adapter: ReplyAdapter, target: Comment, state_path: Path) -> dict:
    """Test selection independently, then send to the explicitly owned test target."""
    fixture = replace(
        target,
        is_own=False,
        author_id="test-fixture",
        text="So cute! 🐾",
        created_at=datetime.now(timezone.utc).isoformat(),
        answered=False,
    )
    assert pick_replies([fixture], ReplyPolicy(rate=1, daily_cap=1))
    assert not pick_replies([replace(fixture, text="How can I adopt?")], ReplyPolicy(rate=1))
    assert not pick_replies([replace(fixture, is_own=True)], ReplyPolicy(rate=1))
    state = {"processed": {}}
    proposals = [(target, "Meow meow! 😸")]
    first = send_proposals(proposals, [adapter], state, state_path)
    if not first or not first[0]["success"]:
        return {"status": "failed", "reason": "Send failed or outcome uncertain; do not retry blindly"}
    # Reload the real saved state rather than relying on process memory.
    restored = json.loads(state_path.read_text())
    assert send_proposals(proposals, [adapter], restored, state_path) == []
    entry = restored["processed"][target.key]
    return {
        "status": "sent",
        "reply_id": entry["reply_id"],
        "question_skipped": True,
        "self_comment_skipped": True,
        "duplicate_skipped": True,
        "text": proposals[0][1],
    }


def mastodon_test() -> dict:
    token = (os.environ.get("MASTODON_TOKEN") or "").strip()
    if not token:
        return {"status": "blocked", "reason": "No Mastodon test token"}
    adapter = MastodonReplies()
    headers = {"Authorization": f"Bearer {token}"}
    account = request("GET", f"{adapter.base}/api/v1/accounts/verify_credentials", headers=headers)
    if account["acct"].casefold() == "cutepetsboston":
        return {"status": "blocked", "reason": "Test token resolves to production account; refusing test posts"}
    root = request(
        "POST",
        f"{adapter.base}/api/v1/statuses",
        headers={**headers, "Idempotency-Key": f"reply-test-{os.environ.get('GITHUB_RUN_ID', 'manual')}"},
        data={"status": "Temporary CutePetsBoston reply-engine test 🐾", "visibility": "unlisted"},
    )
    save_json(Path("mastodon-test-root.json"), {"id": root["id"], "url": root.get("url")})
    target = Comment(
        platform="Mastodon",
        comment_id=root["id"],
        root_id=root["id"],
        author_id=account["id"],
        author=account["acct"],
        text=root["content"],
        created_at=root["created_at"],
        is_own=True,
        context={"visibility": "unlisted"},
    )
    result = exercise(adapter, target, Path("mastodon-live-state.json"))
    result["test_thread"] = root.get("url")
    if result["status"] != "sent":
        return result
    saved = request("GET", f"{adapter.base}/api/v1/statuses/{result['reply_id']}", headers=headers)
    assert saved["in_reply_to_id"] == root["id"]
    assert saved["account"]["id"] == account["id"]
    assert "Meow meow!" in saved["content"]
    post: PublishedPost = {
        "pet_id": "test",
        "platform": "Mastodon",
        "post_id": root["id"],
        "posted_at": datetime.now(timezone.utc).isoformat(),
    }
    for attempt in range(5):
        comments = adapter.read(post)
        if any(comment.comment_id == result["reply_id"] for comment in comments):
            assert not pick_replies(comments, ReplyPolicy(rate=1))
            result.update(status="passed", reply_url=saved.get("url"), readback_verified=True)
            return result
        time.sleep(2)
    raise ValueError("Sent reply was not visible in the test thread; do not resend")


def instagram_test() -> dict:
    adapter = InstagramReplies()
    if not adapter.token or not adapter.account_id:
        return {"status": "blocked", "reason": "No Instagram test account credentials"}
    headers = {"Authorization": f"Bearer {adapter.token}"}
    account = request(
        "GET", f"{GRAPH_API_BASE}/{adapter.account_id}", headers=headers, params={"fields": "id,username"}
    )
    if account["username"].casefold() == "cutepetsboston":
        return {"status": "blocked", "reason": "Test credentials resolve to production; refusing test replies"}
    media = request(
        "GET",
        f"{GRAPH_API_BASE}/{adapter.account_id}/media",
        headers=headers,
        params={"fields": "id,permalink", "limit": 5},
    )
    for item in media.get("data", []):
        post: PublishedPost = {
            "pet_id": "test",
            "platform": "Instagram",
            "post_id": item["id"],
            "posted_at": datetime.now(timezone.utc).isoformat(),
        }
        comments = adapter.read(post)
        if not comments:
            continue
        target = comments[0]
        result = exercise(adapter, target, Path("instagram-live-state.json"))
        result["test_thread"] = item.get("permalink")
        if result["status"] == "sent":
            saved = request(
                "GET", f"{GRAPH_API_BASE}/{result['reply_id']}", headers=headers, params={"fields": "id,text"}
            )
            assert saved["text"] == result["text"]
            result.update(status="passed", readback_verified=True)
        return result
    return {"status": "blocked", "reason": "Test account has no existing comments to reply to"}


def main() -> None:
    results: dict[str, dict] = {
        "Bluesky": {"status": "blocked", "reason": "No Bluesky test-account secrets configured"}
    }
    for name, run in (("Mastodon", mastodon_test), ("Instagram", instagram_test)):
        try:
            results[name] = run()
        except requests.HTTPError as exc:
            code = exc.response.status_code if exc.response is not None else None
            results[name] = {
                "status": "blocked" if code in (401, 403) else "failed",
                "reason": f"HTTP {code}; inspect account access before retrying",
            }
            if exc.response is not None:
                try:
                    error = exc.response.json().get("error", {})
                    if isinstance(error, dict):
                        results[name]["api_code"] = error.get("code")
                        message = str(error.get("message", ""))
                        for key in ("MASTODON_TOKEN", "INSTAGRAM_PAGE_ACCESS_TOKEN"):
                            secret = os.environ.get(key)
                            if secret:
                                message = message.replace(secret, "[redacted]")
                        results[name]["api_message"] = message[:300]
                except ValueError:
                    pass
        except (requests.RequestException, ValueError, AssertionError) as exc:
            results[name] = {"status": "failed", "reason": type(exc).__name__ + "; do not resend blindly"}
        save_json(Path("reply-live-test-results.json"), results)
    print(json.dumps(results, ensure_ascii=False, indent=2))
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as output:
            for name, result in results.items():
                output.write(f"- {name}: {result['status']} {result.get('reason', '')}\n")
    if any(result["status"] == "failed" for result in results.values()):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
