"""Debug poster that prints post content instead of publishing."""

from abstractions import AdoptablePet, Post, PostResult, SocialPoster


class PosterDebug(SocialPoster):
    def __init__(self, stream=None):
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
            f"Image: {post.image_url}\n"
            f"Link: {post.link}\n"
            f"Alt: {post.alt_text}\n"
            f"Tags: {post.tags}\n"
        )
        if self.stream:
            self.stream.write(output)
        else:
            print(output)
        return PostResult(success=True, post_id="debug")
