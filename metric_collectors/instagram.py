"""Instagram engagement metric collector."""

from datetime import datetime, timezone
import os

import requests

from abstractions import MetricCollector, PostMetrics
from social_posters.instagram import GRAPH_API_BASE


class CollectorInstagram(MetricCollector):
    def __init__(self, access_token=None):
        self.access_token = access_token or os.environ.get(
            "INSTAGRAM_PAGE_ACCESS_TOKEN"
        )

    @property
    def platform_name(self) -> str:
        return "Instagram"

    def fetch_metrics(
        self, post_id: str, post_url: str | None = None
    ) -> PostMetrics | None:
        if not self.access_token:
            print(
                f"Instagram metric collection failed for {post_id}: "
                "access token missing"
            )
            return None

        try:
            response = requests.get(
                f"{GRAPH_API_BASE}/{post_id}",
                params={
                    "fields": "like_count,comments_count",
                    "access_token": self.access_token,
                },
                timeout=20,
            )
            response.raise_for_status()
            media = response.json()
            return PostMetrics(
                collected_at=datetime.now(timezone.utc).isoformat(),
                likes=media.get("like_count"),
                reposts=None,
                comments=media.get("comments_count"),
            )
        except Exception as exc:
            print(f"Instagram metric collection failed for {post_id}: {exc}")
            return None
