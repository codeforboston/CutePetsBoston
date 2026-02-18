import os
import tempfile
from urllib.parse import urlparse
from typing import Optional

import requests
from instapy import InstaPy

from abstractions import Post, PostResult, SocialPoster


class PosterInstagram(SocialPoster):
    def __init__(self):
        # Handle environment variable validation internally
        self.username = os.environ.get("INSTAGRAM_HANDLE")
        self.password = os.environ.get("INSTAGRAM_PASSWORD")
        self._session = None
        self._is_available = bool(self.username and self.password)

    @property
    def platform_name(self) -> str:
        return "Instagram"

    def authenticate(self) -> bool:
        try:
            self._session = InstaPy(
                username=self.username,
                password=self.password,
                headless_browser=True,
            )
            self._session.login()
            return True
        except Exception:
            self._session = None
            return False

    def publish(self, post: Post) -> PostResult:
        if not self._is_available:
            return PostResult(
                success=False,
                error_message="Instagram credentials not available.",
            )

        if not post.image_url:
            return PostResult(
                success=False,
                error_message="Instagram posts require an image URL.",
            )

        if not self._session and not self.authenticate():
            return PostResult(
                success=False,
                error_message="Instagram authentication failed.",
            )

        image_path = None
        try:
            image_path = self._download_image(post.image_url)
            caption = self._format_caption(post)
            self._session.upload_photo(image_path, caption=caption)
            return PostResult(success=True)
        except Exception as exc:
            return PostResult(success=False, error_message=str(exc))
        finally:
            if self._session:
                self._session.end()
                self._session = None
            if image_path and os.path.exists(image_path):
                os.unlink(image_path)

    def _format_caption(self, post: Post) -> str:
        caption = post.text
        if post.tags:
            tags = " ".join(f"#{tag}" for tag in post.tags if tag)
            caption = f"{caption}\n\n{tags}"
        return caption[:2200]

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
