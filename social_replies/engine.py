"""Deterministic sampling and limits; incoming text never becomes instructions."""

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

from social_replies.models import Comment

POOL_PATH = Path(__file__).with_name("replies.json")
SUBSTANTIVE = re.compile(
    r"\b(adopt|adoption|available|apply|application|fee|where|how|help|"
    r"died|dead|death|sorry|lost|sick|scam|spam|rip)\b|passed away",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class ReplyPolicy:
    rate: float = 1 / 3
    daily_cap: int = 5
    max_age_days: int = 7

    def __post_init__(self) -> None:
        if not 0 <= self.rate <= 1 or self.daily_cap < 0 or self.max_age_days < 1:
            raise ValueError("Invalid reply rate, daily cap, or age window")


def pick_replies(
    comments: list[Comment],
    policy: ReplyPolicy,
    history: dict[str, str] | None = None,
    now: datetime | None = None,
    blocked_threads: set[str] | None = None,
) -> list[tuple[Comment, str]]:
    """Propose at most one reply per thread per run, from a shared silly pool.

    history maps successfully replied-to comment keys to UTC timestamps.
    The caller must supply durable history before using proposals for sending.
    """
    now = now or datetime.now(timezone.utc)
    history = history or {}
    today = now.date()
    used_today = sum(datetime.fromisoformat(stamp).date() == today for stamp in history.values())
    remaining = max(0, policy.daily_cap - used_today)
    pool: list[str] = json.loads(POOL_PATH.read_text(encoding="utf-8"))
    selected: list[tuple[Comment, str]] = []
    threads = set(blocked_threads or ())
    seen: set[str] = set()
    for comment in sorted(comments, key=lambda item: (item.created_at, item.key)):
        if len(selected) >= remaining:
            break
        if comment.key in seen or comment.key in history or comment.thread_key in threads:
            continue
        seen.add(comment.key)
        if comment.is_own or comment.is_bot or comment.answered or not comment.author_id:
            continue
        if not comment.text.strip() or len(comment.text) > 120:
            continue
        if "?" in comment.text or "http" in comment.text.casefold() or SUBSTANTIVE.search(comment.text):
            continue
        try:
            created = datetime.fromisoformat(comment.created_at.replace("Z", "+00:00"))
            if not now - timedelta(days=policy.max_age_days) <= created <= now:
                continue
        except ValueError, TypeError:
            continue
        digest = hashlib.sha256(comment.key.encode()).digest()
        if int.from_bytes(digest[:8], "big") / 2**64 >= policy.rate:
            continue
        index = int.from_bytes(digest[8:16], "big") % len(pool)
        if selected and pool[index] == selected[-1][1]:
            index = (index + 1) % len(pool)
        selected.append((comment, pool[index]))
        threads.add(comment.thread_key)
    return selected
