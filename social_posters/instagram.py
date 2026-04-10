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
            print("Instagram: credentials not set (INSTAGRAM_BUSINESS_ACCOUNT_ID or INSTAGRAM_PAGE_ACCESS_TOKEN missing)")
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
        except requests.exceptions.HTTPError as exc:
            body = exc.response.text if exc.response is not None else "no response body"
            print(f"Instagram auth failed (HTTP {exc.response.status_code}): {body}")
            self._authenticated = False
            return False
        except Exception as exc:
            print(f"Instagram auth failed: {exc}")
            self._authenticated = False
            return False

    def is_authenticated(self) -> bool:
        return self._authenticated

    def publish(self, post: Post) -> PostResult:
        if not self._is_available:
            return PostResult(success=False, error_message="Instagram credentials not available.")

        if not post.image_url:
            return PostResult(success=False, error_message="Instagram posts require an image URL.")

        if not self._authenticated and not self.authenticate():
            return PostResult(success=False, error_message="Instagram authentication failed.")

        try:
            container_id = self._create_media_container(post)
            media_id = self._publish_media(container_id)
            return PostResult(
                success=True,
                post_id=media_id,
                post_url="https://www.instagram.com/cute.pets.boston/",
            )
        except requests.exceptions.HTTPError as exc:
            body = exc.response.text if exc.response is not None else "no response body"
            error = f"Instagram publish failed (HTTP {exc.response.status_code}): {body}"
            print(error)
            return PostResult(success=False, error_message=error)
        except Exception as exc:
            error = f"Instagram publish failed: {exc}"
            print(error)
            return PostResult(success=False, error_message=error)

    def _create_media_container(self, post: Post) -> str:
        """Create a media container and return its ID."""
        caption = self._format_caption(post)
        response = requests.post(
            f"{GRAPH_API_BASE}/{self.account_id}/media",
            data={
                "image_url": post.image_url,
                "caption": caption,
                "access_token": self.access_token,
            },
            timeout=30,
        )
        response.raise_for_status()
        return response.json()["id"]

    def _publish_media(self, container_id: str) -> str:
        response = requests.post(
            f"{GRAPH_API_BASE}/{self.account_id}/media_publish",
            data={
                "creation_id": container_id,
                "access_token": self.access_token,
            },
            timeout=30,
        )
        response.raise_for_status()
        return response.json()["id"]

    def _format_caption(self, post: Post) -> str:
        caption = post.text
        if post.tags:
            tags = " ".join(f"#{tag}" for tag in post.tags if tag)
            caption = f"{caption}\n\n{tags}"
        return caption[:2200]
