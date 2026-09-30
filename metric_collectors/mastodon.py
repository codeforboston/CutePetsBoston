"""Mastodon engagement metric collector."""

import os
from datetime import datetime, timezone
from typing import Protocol, TypedDict

from mastodon import Mastodon

from abstractions import MetricCollector, PostMetrics


class StatusCounts(TypedDict, total=False):
    favourites_count: int | None
    reblogs_count: int | None
    replies_count: int | None


class MastodonStatusClient(Protocol):
    def status(self, post_id: str, /) -> StatusCounts: ...


class _MastodonStatusAdapter:
    """Expose only the SDK response fields used by metric collection."""

    def __init__(self, client: Mastodon) -> None:
        self._client = client

    def status(self, post_id: str, /) -> StatusCounts:
        status = self._client.status(post_id)
        return {
            "favourites_count": status.get("favourites_count"),
            "reblogs_count": status.get("reblogs_count"),
            "replies_count": status.get("replies_count"),
        }


class CollectorMastodon(MetricCollector):
    def __init__(self, client: MastodonStatusClient | None = None) -> None:
        api_base_url = os.environ.get(
            "MASTODON_API_BASE_URL", "https://mastodon.social"
        )
        self._client: MastodonStatusClient = client or _MastodonStatusAdapter(
            Mastodon(api_base_url=api_base_url)
        )

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
