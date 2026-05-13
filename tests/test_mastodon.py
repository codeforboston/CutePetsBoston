from abstractions import Post
from social_posters.mastodon import PosterMastodon, MASTODON_CHARACTER_LIMIT


class TestMastodonCaption:
    def setup_method(self):
        self.poster = PosterMastodon.__new__(PosterMastodon)

    def reconstruct_text(self, main_caption: str, replies: list[str]) -> str:
        main_without_tags = main_caption.split("\n\n#")[0]
        main_without_suffix = (
            main_without_tags
            .replace("...", "")
            .replace("\n\nMore details below ⬇️", "")
            .strip()
        )

        return " ".join([main_without_suffix] + replies).strip()
    
    def test_thread_preserves_original_text_content(self):
        original_text = " ".join(f"word{i}" for i in range(300))
        post = Post(text=original_text, tags=["AdoptDontShop", "Boston"])

        main_caption, replies = self.poster._format_caption_thread(post)

        reconstructed = self.reconstruct_text(main_caption, replies)

        assert reconstructed == original_text

    def test_thread_preserves_original_text_without_spaces(self):
        original_text = "x" * 1000
        post = Post(text=original_text, tags=["AdoptDontShop", "Boston"])

        main_caption, replies = self.poster._format_caption_thread(post)

        main_without_tags = main_caption.split("\n\n#")[0]
        main_without_suffix = (
            main_without_tags
            .replace("...", "")
            .replace("\n\nMore details below ⬇️", "")
            .strip()
        )

        reconstructed = main_without_suffix + "".join(replies)

        assert reconstructed == original_text

    def test_no_tags(self):
        post = Post(text="Hello, world!")
        main_caption, replies = self.poster._format_caption_thread(post) 
        assert main_caption == "Hello, world!"
        assert replies == []

    def test_with_tags(self):
        post = Post(text="Meet Poppy!", tags=["AdoptDontShop", "Boston"])
        main_caption, replies = self.poster._format_caption_thread(post)

        assert main_caption == "Meet Poppy!\n\n#AdoptDontShop #Boston"
        assert replies == []

    def test_caption_stays_under_limit_and_creates_reply(self):
        post = Post(text="x " * 1000, tags=["AdoptDontShop", "Boston"])
        main_caption, replies = self.poster._format_caption_thread(post)

        assert len(main_caption) <= MASTODON_CHARACTER_LIMIT
        assert main_caption.endswith("\n\n#AdoptDontShop #Boston")
        assert "..." in main_caption
        assert "More details below" in main_caption
        assert replies
        assert all(len(reply) <= MASTODON_CHARACTER_LIMIT for reply in replies)

    def test_caption_stays_under_limit_creates_reply(self):
        post = Post(text="x" * 1000, tags=["AdoptDontShop", "Boston"])
        main_caption, replies = self.poster._format_caption_thread(post)

        assert len(main_caption) <= MASTODON_CHARACTER_LIMIT
        assert main_caption.endswith("\n\n#AdoptDontShop #Boston")
        assert "..." in main_caption
        assert "More details below" in main_caption
        assert replies
        assert all(len(reply) <= MASTODON_CHARACTER_LIMIT for reply in replies)

    def test_empty_tags_are_ignored(self):
        post = Post(text="Meet Poppy!", tags=["AdoptDontShop", "", None, "Boston"])
        main_caption, replies = self.poster._format_caption_thread(post)

        assert main_caption == "Meet Poppy!\n\n#AdoptDontShop #Boston"
        assert replies == []
    
    def test_long_text_without_tags_creates_replies(self):
        post = Post(text="hello " * 300)
        main_caption, replies = self.poster._format_caption_thread(post)

        assert len(main_caption) <= MASTODON_CHARACTER_LIMIT
        assert replies
        assert all(len(reply) <= MASTODON_CHARACTER_LIMIT for reply in replies)
    
    def test_safe_truncate_does_not_split_words_when_possible(self):
        kept, remaining = self.poster._safe_truncate("hello world again", 12)
        assert kept == "hello world"
        assert remaining == "again"








































