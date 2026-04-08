import os

import requests

from abstractions import Post, PostResult, SocialPoster


GRAPH_API_VERSION = "v21.0"
GRAPH_API_BASE = f"https://graph.facebook.com/{GRAPH_API_VERSION}"


class PosterInstagram(SocialPoster):
    def __init__(self):
        self.account_id = os.environ.get("INSTAGRAM_BUSINESS_ACCOUNT_ID")
        self.access_token = os.environ.get("INSTAGRAM_PAGE_ACCESS_TOKEN")
        self._is_available = bool(self.account_id and self.access_token)
        self._authenticated = False

    @property
    def platform_name(self) -> str:
        return "Instagram"

    def authenticate(self) -> bool:
        if not self._is_available:
            return False
        try:
            response = requests.get(
                f"{GRAPH_API_BASE}/{self.account_id}",
                params={"fields": "id,username", "access_token": self.access_token},
                timeout=10,
            )
            response.raise_for_status()
            self._authenticated = True
            return True
        except Exception:
            self._authenticated = False
            return False
