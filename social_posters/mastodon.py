from datetime import datetime
from typing import Optional
import os
import mastodon import Mastodon

import requests

from abstractions import Post, PostResult, SocialPoster

class PosterMastodon(SocialPoster):
    def __init__(self):
        # Handle environment variable validation internally
        self.username = os.environ.get("MASTODON_ID")
        self.token = os.environ.get("MASTODON.TOKEN")
        self.password = os.environ.get("MASTODON_PASSWORD")
        self._session = None
        self._is_available = bool(self.username and self.password)

    # public functions: platform, authenticate, publish
    @property
    def platform_name(self) -> str:
        return "Mastodon"
    
    # 
    def authenticate(self) -> bool:
        try:
            self._session = Mastodon(
                access_token=self.token,
                api_base_url='mastodon.social'
            )
            return True
        except Exception:
            self._session = None
            return False
        

    def publish(self, post: Post) -> PostResult:
        mastodon.status_post("Hello World!")
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
                error_message="Mastodon authentication failed.",
            )

        image_path = None
        try:
            image_path = self._download_image(post.image_url)
            caption = self._format_caption(post)
            image = self._session.media_post("example.png",
                                            mime_type ="image/png",
                                            description =caption)
            self._session.status_post("Hello, world!", media_ids=image["id"])
            return PostResult(success=True)
        except Exception as exc:
            return PostResult(success=False, error_message=str(exc))
        finally:
            if self._session:
                #self._session.end()
                self._session = None
            if image_path and os.path.exists(image_path):
                os.unlink(image_path)

    # private methods for _methodname
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