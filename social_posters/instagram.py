import os
import tempfile
from pathlib import Path
from urllib.parse import urlparse

import requests
from instagrapi import Client

from abstractions import Post, PostResult, SocialPoster


class PosterInstagram(SocialPoster):
    def __init__(self):
        self.username = os.environ.get("INSTAGRAM_HANDLE")
        self.password = os.environ.get("INSTAGRAM_PASSWORD")
        self._client = None
        self._is_available = bool(self.username and self.password)

    @property
    def platform_name(self) -> str:
        return "Instagram"

    def authenticate(self) -> bool:
        try:
            self._client = Client()
            # Use proxy if available to maintain a consistent IP, running on a private VPS using a proxy service so lowkey gonna need a better fix
            proxy = os.environ.get("INSTAGRAM_PROXY")
            if proxy:
                self._client.set_proxy(proxy)
            session_file = Path("ig_session.json")
            # Reuse saved session to avoid repeated logins, as per instagrapi best practices
            if session_file.exists():
                self._client.load_settings(str(session_file))
            # Login
            self._client.login(self.username, self.password)
            # Save session 
            self._client.dump_settings(str(session_file))
            return True
        except Exception:
            self._client = None
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

        if not self._client and not self.authenticate():
            return PostResult(
                success=False,
                error_message="Instagram authentication failed.",
            )

        image_path = None
        try:
            image_path = self._download_image(post.image_url)
            caption = self._format_caption(post)
            media = self._client.photo_upload(image_path, caption=caption)
            return PostResult(
                success=True,
                post_id=str(media.pk),  # Instagrams unique numeric ID for this post
                post_url=f"https://www.instagram.com/p/{media.code}/",  # Public URL to view post
            )
        except Exception as exc:
            return PostResult(success=False, error_message=str(exc))
        finally:
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
