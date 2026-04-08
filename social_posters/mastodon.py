import os
from urllib.parse import urlparse
import tempfile

import requests
from mastodon import Mastodon

from abstractions import Post, PostResult, SocialPoster

MASTODON_CHARACTER_LIMIT = 500
ELLIPSIS = "..."


class PosterMastodon(SocialPoster):
    def __init__(self):
        raw_token = os.environ.get("MASTODON_TOKEN")
        self.token = raw_token.strip() if raw_token else None
        self.api_base_url = "https://mastodon.social"
        self._session = None
        self._is_available = bool(self.token)
        self._auth_error = None

    @property
    def platform_name(self) -> str:
        return "Mastodon"

    def authenticate(self) -> bool:
        try:
            self._session = Mastodon(
                access_token=self.token,
                api_base_url=self.api_base_url,
            )
            self._session.account_verify_credentials()
            self._auth_error = None
            return True
        except Exception as exc:
            self._session = None
            self._auth_error = f"{type(exc).__name__}: {exc}"
            return False

    def publish(self, post: Post) -> PostResult:
        if not self._is_available:
            return PostResult(
                success=False,
                error_message="Mastodon credentials not available.",
            )

        if not post.image_url:
            return PostResult(
                success=False,
                error_message="Mastodon posts require an image URL.",
            )

        if not self._session and not self.authenticate():
            return PostResult(
                success=False,
                error_message=(
                    "Mastodon authentication failed."
                    if not self._auth_error
                    else f"Mastodon authentication failed: {self._auth_error}"
                ),
            )

        image_path = None
        try:
            image_path = self._download_image(post.image_url)
            media = self._session.media_post(
                image_path,
                description=post.alt_text or "Photo of an adoptable pet",
            )
            status = self._session.status_post(
                self._format_caption(post),
                media_ids=[media["id"]],
            )
            return PostResult(
                success=True,
                post_id=str(status["id"]),
                post_url=status.get("url"),
            )
        except Exception as exc:
            return PostResult(success=False, error_message=str(exc))
        finally:
            self._session = None
            if image_path and os.path.exists(image_path):
                os.unlink(image_path)

    def _format_caption(self, post: Post) -> str:
        tags = " ".join(f"#{tag}" for tag in post.tags if tag)
        suffix = f"\n\n{tags}" if tags else ""
        available_text_length = MASTODON_CHARACTER_LIMIT - len(suffix)

        if available_text_length <= len(ELLIPSIS):
            return (suffix[-MASTODON_CHARACTER_LIMIT:]).strip()

        caption_text = post.text.strip()
        if len(caption_text) > available_text_length:
            caption_text = caption_text[: available_text_length - len(ELLIPSIS)].rstrip()
            caption_text = f"{caption_text}{ELLIPSIS}"

        return f"{caption_text}{suffix}"

    def _download_image(self, image_url: str) -> str:
        parsed = urlparse(image_url)
        ext = os.path.splitext(parsed.path)[1] or ".jpg"
        with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
            response = requests.get(image_url, stream=True, timeout=20)
            response.raise_for_status()
            for chunk in response.iter_content(chunk_size=1024 * 128):
                if chunk:
                    tmp.write(chunk)
            return tmp.name