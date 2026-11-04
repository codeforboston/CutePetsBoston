"""Collect comments and preview playful replies. Sending requires explicit --send."""

import argparse
import json
import os
from contextlib import ExitStack, contextmanager
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterator

import requests

from database import PublishedPost, read_database
from social_replies.adapters import BlueskyReplies, InstagramReplies, MastodonReplies
from social_replies.engine import ReplyPolicy, pick_replies
from social_replies.models import Comment, ReplyAdapter


def save_json(path: Path, value: object) -> None:
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)


@contextmanager
def sending_lock(state_path: Path) -> Iterator[None]:
    """Concurrent senders must share this lock as well as the state file."""
    lock_path = state_path.with_name(state_path.name + ".lock")
    descriptor = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    os.close(descriptor)
    try:
        yield
    finally:
        lock_path.unlink()


def audit(
    database: Path,
    adapters: list[ReplyAdapter],
    days: int = 30,
    posts_per_platform: int = 30,
) -> tuple[list[Comment], dict]:
    data = read_database(database)
    posts = data.get("posts", [])
    if not posts:
        raise ValueError("No saved social posts found; provide the production database.json artifact")
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    comments: dict[str, Comment] = {}
    coverage = {}
    for adapter in adapters:
        candidates = [
            post
            for post in posts
            if post["platform"] == adapter.platform_name
            and post.get("post_id")
            and datetime.fromisoformat(post["posted_at"]) >= cutoff
        ]

        # Look at known conversations first, then fill the sample with recent posts.
        def priority(post: PublishedPost) -> tuple[bool, str]:
            engaged = any((snapshot.get("comments") or 0) > 0 for snapshot in post.get("metrics", []))
            return engaged, post["posted_at"]

        candidates.sort(key=priority, reverse=True)
        status: dict = {"available_posts": len(candidates), "checked_posts": 0, "errors": [], "stopped_early": False}
        coverage[adapter.platform_name] = status
        for post in candidates[:posts_per_platform]:
            try:
                for comment in adapter.read(post):
                    comments[comment.key] = comment
                status["checked_posts"] += 1
            except (requests.RequestException, ValueError, KeyError) as exc:
                # Do not log credentials or full request/response payloads.
                response = exc.response if isinstance(exc, requests.HTTPError) else None
                code = response.status_code if response is not None else None
                error: dict = {"post_id": post["post_id"], "error": type(exc).__name__, "http_status": code}
                if response is not None:
                    try:
                        detail = response.json().get("error", {})
                        if isinstance(detail, dict):
                            error["api_code"] = detail.get("code")
                            message = str(detail.get("message", ""))
                            token = getattr(adapter, "token", None)
                            error["message"] = message.replace(token, "[redacted]")[:300] if token else message[:300]
                    except ValueError:
                        pass
                status["errors"].append(error)
                if isinstance(exc, ValueError) or code in (400, 401, 403, 429):
                    status["stopped_early"] = True
                    break
        status["comments"] = sum(comment.platform == adapter.platform_name for comment in comments.values())
        status["own_comments"] = sum(
            comment.platform == adapter.platform_name and comment.is_own for comment in comments.values()
        )
        status["external_comments"] = (
            status["comments"] - status["own_comments"] if status["checked_posts"] or not status["errors"] else None
        )
    return list(comments.values()), coverage


def send_proposals(
    proposals: list[tuple[Comment, str]],
    adapters: list[ReplyAdapter],
    state: dict,
    state_path: Path,
) -> list[dict]:
    """Reserve before sending. An uncertain result stays reserved for manual review."""
    by_platform = {adapter.platform_name: adapter for adapter in adapters}
    processed = state.setdefault("processed", {})
    results = []
    for comment, text in proposals:
        if comment.key in processed:
            continue
        entry: dict = {
            "at": datetime.now(timezone.utc).isoformat(),
            "thread": comment.thread_key,
            "status": "pending",
            "text": text,
        }
        processed[comment.key] = entry
        save_json(state_path, state)
        try:
            result = by_platform[comment.platform].reply(comment, text)
            if result.success:
                entry.update(status="sent", reply_id=result.post_id)
            else:
                entry["status"] = "needs_review"
            results.append({"comment": comment.key, "success": result.success})
        except requests.RequestException:
            entry["status"] = "needs_review"
            results.append({"comment": comment.key, "success": False})
        save_json(state_path, state)
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, default=Path("database.json"))
    parser.add_argument("--output", type=Path, default=Path("reply-inbox.json"))
    parser.add_argument("--state", type=Path, default=Path("reply-state.json"))
    parser.add_argument("--days", type=int, default=30)
    parser.add_argument("--posts-per-platform", type=int, default=30)
    parser.add_argument("--rate", type=float, default=1 / 3)
    parser.add_argument("--daily-cap", type=int, default=5)
    parser.add_argument("--send", action="store_true", help="Send real replies; reuse the same durable state file")
    args = parser.parse_args()
    if args.days < 1 or args.posts_per_platform < 1:
        parser.error("Days and posts-per-platform must be positive")
    policy = ReplyPolicy(rate=args.rate, daily_cap=args.daily_cap)
    with ExitStack() as stack:
        if args.send:
            stack.enter_context(sending_lock(args.state))
        run(args, policy)


def run(args: argparse.Namespace, policy: ReplyPolicy) -> None:
    # Broken state must fail loudly; resetting it could resend replies.
    state = json.loads(args.state.read_text(encoding="utf-8")) if args.state.exists() else {"processed": {}}
    if not isinstance(state, dict) or not isinstance(state.get("processed"), dict):
        raise ValueError("Invalid reply state")
    adapters: list[ReplyAdapter] = [BlueskyReplies(), MastodonReplies(), InstagramReplies()]
    comments, coverage = audit(args.database, adapters, args.days, args.posts_per_platform)
    history = {key: entry["at"] for key, entry in state["processed"].items()}
    blocked = {entry["thread"] for entry in state["processed"].values()}
    proposals = pick_replies(comments, policy, history, blocked_threads=blocked)
    report: dict = {
        "mode": "send" if args.send else "preview",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "policy": asdict(policy),
        "coverage": coverage,
        "comments": [asdict(comment) for comment in comments],
        "proposals": [{"comment": comment.key, "text": text} for comment, text in proposals],
    }
    save_json(args.output, report)
    print(json.dumps({"mode": report["mode"], "coverage": coverage, "proposed_replies": len(proposals)}, indent=2))
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as output:
            output.write("## Social reply audit (preview)\n\n")
            for platform, status in coverage.items():
                count = status["external_comments"]
                label = str(count) if count is not None else "unavailable"
                output.write(
                    f"- {platform}: {status['checked_posts']} posts checked, {label} audience comments, "
                    f"{status['own_comments']} own comments, {len(status['errors'])} read errors\n"
                )
            output.write(f"\n{len(proposals)} playful replies proposed. Download reply-inbox.json for the comments.\n")
    if args.send:
        report["results"] = send_proposals(proposals, adapters, state, args.state)
        save_json(args.output, report)


if __name__ == "__main__":
    main()
