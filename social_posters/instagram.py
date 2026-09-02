import os
import time

import requests

from abstractions import Post, PostResult, SocialPoster


GRAPH_API_VERSION = "v26.0"
GRAPH_API_BASE = f"https://graph.instagram.com/{GRAPH_API_VERSION}"

# Images typically finish container processing in seconds; 
# video would need Meta's suggested ~1-minute cadence
CONTAINER_POLL_INTERVAL_SECONDS = 5
CONTAINER_POLL_TIMEOUT_SECONDS = 60


class PosterInstagram(SocialPoster):
    def __init__(self):
        self.account_id = os.environ.get("INSTAGRAM_BUSINESS_ACCOUNT_ID")
        self.access_token = os.environ.get("INSTAGRAM_PAGE_ACCESS_TOKEN")
        self._is_available = bool(self.account_id and self.access_token)
        self._authenticated = False
        self.username = None

    @property
    def platform_name(self) -> str:
        return "Instagram"

    @property
    def _authorization_headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.access_token}"}

    def authenticate(self) -> bool:
        if not self._is_available:
            print("Instagram: credentials not set (INSTAGRAM_BUSINESS_ACCOUNT_ID or INSTAGRAM_PAGE_ACCESS_TOKEN missing)")
            return False
        try:
            response = requests.get(
                f"{GRAPH_API_BASE}/{self.account_id}",
                params={"fields": "id,username"},
                headers=self._authorization_headers,
                timeout=10,
            )
            response.raise_for_status()
            self.username = response.json().get("username")
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
            self._wait_for_container_ready(container_id)

            media_id = self._publish_media(container_id)
            post_url = (
                f"https://www.instagram.com/{self.username}/" if self.username else None
            )
            return PostResult(
                success=True,
                post_id=media_id,
                post_url=post_url,
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
            headers=self._authorization_headers,
            data={
                "image_url": post.image_url,
                "caption": caption,
            },
            timeout=30,
        )
        response.raise_for_status()
        return response.json()["id"]

    def _wait_for_container_ready(self, container_id: str) -> None:
        """Poll the container until Instagram finishes processing the image.

        Publishing before the container is FINISHED returns "Media ID is not
        available" (error 9007).
        """
        deadline = time.monotonic() + CONTAINER_POLL_TIMEOUT_SECONDS
        while True:
            response = requests.get(
                f"{GRAPH_API_BASE}/{container_id}",
                params={"fields": "status_code"},
                headers=self._authorization_headers,
                timeout=10,
            )
            response.raise_for_status()
            status = response.json().get("status_code")

            if status == "FINISHED":
                return
            if status in ("ERROR", "EXPIRED"):
                raise RuntimeError(
                    f"Instagram media container {container_id} failed with status {status}"
                )
            if time.monotonic() >= deadline:
                raise RuntimeError(
                    f"Instagram media container {container_id} did not finish "
                    f"processing within {CONTAINER_POLL_TIMEOUT_SECONDS}s "
                    f"(last status: {status})"
                )
            time.sleep(CONTAINER_POLL_INTERVAL_SECONDS)

    def _publish_media(self, container_id: str) -> str:
        response = requests.post(
            f"{GRAPH_API_BASE}/{self.account_id}/media_publish",
            headers=self._authorization_headers,
            data={
                "creation_id": container_id,
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
