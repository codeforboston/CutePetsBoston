"""Bluesky engagement metric collector."""

from datetime import datetime, timezone

import requests

from abstractions import MetricCollector, PostMetrics


POST_THREAD_URL = "https://public.api.bsky.app/xrpc/app.bsky.feed.getPostThread"


class CollectorBluesky(MetricCollector):
    @property
    def platform_name(self) -> str:
        return "Bluesky"

    def fetch_metrics(
        self, post_id: str, post_url: str | None = None
    ) -> PostMetrics | None:
        if not post_url:
            print(f"Bluesky metric collection failed for {post_id}: post URL missing")
            return None

        try:
            response = requests.get(
                POST_THREAD_URL,
                params={"uri": post_url},
                timeout=20,
            )
            response.raise_for_status()
            post = response.json()["thread"]["post"]
            return PostMetrics(
                collected_at=datetime.now(timezone.utc).isoformat(),
                likes=post.get("likeCount"),
                reposts=post.get("repostCount"),
                comments=post.get("replyCount"),
            )
        except Exception as exc:
            print(f"Bluesky metric collection failed for {post_id}: {exc}")
            return None
