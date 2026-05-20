from abstractions import Post
from social_posters.mastodon import PosterMastodon, MASTODON_CHARACTER_LIMIT


class TestMastodonCaption:
    def setup_method(self):
        self.poster = PosterMastodon.__new__(PosterMastodon)

    def test_no_tags(self):
        post = Post(text="Hello, world!")
        assert self.poster._format_caption(post) == "Hello, world!"

    def test_with_tags(self):
        post = Post(text="Meet Poppy!", tags=["AdoptDontShop", "Boston"])
        assert self.poster._format_caption(post) == "Meet Poppy!\n\n#AdoptDontShop #Boston"

    def test_caption_stays_under_limit(self):
        post = Post(text="x" * 1000, tags=["AdoptDontShop", "Boston"])
        caption = self.poster._format_caption(post)

        assert len(caption) <= MASTODON_CHARACTER_LIMIT
        assert caption.endswith("\n\n#AdoptDontShop #Boston")
        assert "..." in caption

    def test_empty_tags_are_ignored(self):
        post = Post(text="Meet Poppy!", tags=["AdoptDontShop", "", None, "Boston"])
        assert self.poster._format_caption(post) == "Meet Poppy!\n\n#AdoptDontShop #Boston"