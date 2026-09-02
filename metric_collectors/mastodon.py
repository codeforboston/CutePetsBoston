"""Mastodon engagement metric collector."""

from datetime import datetime, timezone
import os

from mastodon import Mastodon

from abstractions import MetricCollector, PostMetrics


class CollectorMastodon(MetricCollector):
    def __init__(self, client=None):
        api_base_url = os.environ.get(
            "MASTODON_API_BASE_URL", "https://mastodon.social"
        )
        self._client = client or Mastodon(api_base_url=api_base_url)

    @property
    def platform_name(self) -> str:
        return "Mastodon"

    def fetch_metrics(
        self, post_id: str, post_url: str | None = None
    ) -> PostMetrics | None:
        try:
            status = self._client.status(post_id)
            return PostMetrics(
                collected_at=datetime.now(timezone.utc).isoformat(),
                likes=status.get("favourites_count"),
                reposts=status.get("reblogs_count"),
                comments=status.get("replies_count"),
            )
        except Exception as exc:
            print(f"Mastodon metric collection failed for {post_id}: {exc}")
            return None
