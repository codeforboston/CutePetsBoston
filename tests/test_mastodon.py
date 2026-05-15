from abstractions import Post
from social_posters.mastodon import PosterMastodon, MASTODON_CHARACTER_LIMIT, MAX_REPLIES
from hypothesis import given, strategies as st

"""
Testing includes:
1. Property-based testing (Hypothesis)
2. Unit tests
3. Manual visual inspection in Preview file

Property-based tests:
- Generate randomized text/tag combinations.
- Nondeterministic testing unless specify seeds.
- Verify global invariants such as:
        * captions never exceed Mastodon limits
        * replies never exceed MAX_REPLIES
        * formatter trace matches normal formatter
        * no empty replies are produced

Unit tests:
- Validate specific expected behaviors and edge cases.
- Examples include:
        * truncation behavior
        * capped thread handling
        * reconstruction correctness
        * no-tag formatting
        * tag filtering
        * word-safe truncation
        * long text handling

Manual visual inspection:
- See Preview file for details
"""

# Generation rules for tags/texts used in testing
tag_strategy = st.lists(
    st.one_of(st.text(min_size=0, max_size=20), st.none()),
    max_size=10
)

text_strategy = st.text(
    alphabet=st.characters(blacklist_categories=("Cs",)),
    min_size=0,
    max_size=5000
)

class TestMastodonCaptionProperties:
    def setup_method(self):
        self.poster = PosterMastodon.__new__(PosterMastodon)
    
    @given(text=text_strategy, tags=tag_strategy)
    def test_all_parts_stay_under_mastodon_limit(self, text, tags):
        post = Post(text=text, tags=tags)

        main_caption, replies = self.poster._format_caption_thread(post)

        assert len(main_caption) <= MASTODON_CHARACTER_LIMIT
        assert all(len(reply) <= MASTODON_CHARACTER_LIMIT for reply in replies)

    @given(text=text_strategy, tags=tag_strategy)
    def test_reply_count_is_never_over_cap(self, text, tags):
        post = Post(text=text, tags=tags)

        _, replies = self.poster._format_caption_thread(post)

        assert len(replies) <= MAX_REPLIES

    @given(text=st.text(min_size=0, max_size=300))
    def test_no_empty_replies(self, text):
        post = Post(text=text)

        _, replies = self.poster._format_caption_thread(post)

        assert all(reply for reply in replies)

    @given(text=text_strategy, tags=tag_strategy)
    def test_debug_matches_normal_formatter(self, text, tags):
        post = Post(text=text, tags=tags)

        main_caption, replies = self.poster._format_caption_thread(post)
        debug_main, debug_replies, debug = self.poster._format_caption_thread_with_trace(post)

        assert debug_main == main_caption
        assert debug_replies == replies
        assert debug.main_caption == main_caption
        assert debug.replies == replies

    @given(text=text_strategy, tags=tag_strategy)
    def test_trace_matches_regular_formatter(self, text, tags):
        post = Post(text=text, tags=tags)

        main_caption, replies = self.poster._format_caption_thread(post)
        trace_main, trace_replies, trace = self.poster._format_caption_thread_with_trace(post)

        assert trace_main == main_caption
        assert trace_replies == replies
        assert trace.main_caption == main_caption
        assert trace.replies == replies


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

    def test_reply_count_is_capped(self):
        post = Post(text="hello " * 5000)

        _, replies = self.poster._format_caption_thread(post)

        assert len(replies) <= MAX_REPLIES

    def test_last_reply_has_truncation_suffix_when_capped(self):
        post = Post(text="hello " * 5000)

        _, replies = self.poster._format_caption_thread(post)

        assert len(replies) == MAX_REPLIES
        assert replies[-1].endswith("...")
        assert len(replies[-1]) <= MASTODON_CHARACTER_LIMIT
    
    def test_last_reply_has_no_truncation_suffix_when_not_capped(self):
        post = Post(text="hello " * 300)

        _, replies = self.poster._format_caption_thread(post)

        assert replies
        assert len(replies) < MAX_REPLIES
        assert not replies[-1].endswith("...")

    def test_capped_thread_does_not_preserve_all_original_text(self):
        original_text = "hello " * 5000
        post = Post(text=original_text)

        main_caption, replies = self.poster._format_caption_thread(post)

        reconstructed = self.reconstruct_text(main_caption, replies)

        assert len(replies) == MAX_REPLIES
        assert reconstructed != original_text
        assert replies[-1].endswith("...")
    
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