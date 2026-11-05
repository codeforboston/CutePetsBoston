"""Debug poster that prints post content instead of publishing."""

import logging
from typing import Protocol

from abstractions import Post, PostResult, SocialPoster

logger = logging.getLogger(__name__)


class TextWriter(Protocol):
    def write(self, text: str, /) -> object: ...


class PosterDebug(SocialPoster):
    def __init__(self, stream: TextWriter | None = None) -> None:
        self.stream = stream

    @property
    def platform_name(self) -> str:
        return "Debug"

    def authenticate(self) -> bool:
        return True

    def publish(self, post: Post) -> PostResult:
        output = (
            f"Debug post\n"
            f"Text:\n{post.text}\n"
            f"Images: {post.selected_image_urls}\n"
            f"Link: {post.link}\n"
            f"Alt: {post.alt_text}\n"
            f"Tags: {post.tags}\n"
            f"Url: {post.link}\n"
        )
        if self.stream:
            self.stream.write(output)
        else:
            logger.info(output)
        return PostResult(success=True, post_id="debug")
