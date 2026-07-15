import logging
from unittest.mock import Mock, call

from abstractions import AdoptablePet, Post
from hypothesis import given, strategies as st, assume
import pytest
from social_posters.mastodon import (
    PosterMastodon,
    MASTODON_CHARACTER_LIMIT,
    MAX_REPLIES,
)


tag_strategy = st.lists(
    st.one_of(st.text(min_size=0, max_size=20), st.none()),
    max_size=10,
)

long_tag_strategy = st.lists(
    st.text(
        alphabet=st.characters(blacklist_categories=("Cs",)),
        min_size=MASTODON_CHARACTER_LIMIT + 1,
        max_size=5000,
    ),
    min_size=1,
    max_size=3,
)

caption_text = st.text(
    alphabet=st.characters(
        blacklist_categories=("Cs", "Cc"),
    ),
    min_size=0,
    max_size=5000,
)

text_strategy = st.text(
    alphabet=st.characters(blacklist_categories=("Cs",)),
    min_size=0,
    max_size=5000,
)

pet_strategy = st.builds(
    AdoptablePet,
    name=st.text(
        alphabet=st.characters(blacklist_categories=("Cs",)),
        min_size=1,
        max_size=20,
    ),
    species=st.sampled_from(
        [
            "Dog",
            "Cat",
            "Rabbit",
            "Bird",
            "Alien",
            "Unknown",
        ]
    ),
    breed=st.text(
        alphabet=st.characters(blacklist_categories=("Cs",)),
        min_size=1,
        max_size=30,
    ),
    location=st.text(
        alphabet=st.characters(blacklist_categories=("Cs",)),
        min_size=1,
        max_size=50,
    ),
    description=text_strategy,
    adoption_url=st.one_of(
        st.none(),
        st.just("https://example.com/adopt"),
    ),
    image_url=st.just("https://example.com/image.jpg"),
    age_string=st.one_of(
        st.none(),
        st.text(
            alphabet=st.characters(blacklist_categories=("Cs",)),
            min_size=1,
            max_size=20,
        ),
    ),
    sex=st.one_of(
        st.none(),
        st.sampled_from(["Male", "Female", "Unknown"]),
    ),
    size_group=st.one_of(
        st.none(),
        st.sampled_from(["Small", "Medium", "Large"]),
    ),
    pet_id=st.one_of(
        st.none(),
        st.text(
            alphabet=st.characters(blacklist_categories=("Cs",)),
            min_size=1,
            max_size=20,
        ),
    ),
)


def reconstruct_text(main_caption: str, replies: list[str]) -> str:
    main_without_tags = main_caption.split("\n\n#")[0]
    main_without_suffix = (
        main_without_tags
        .replace("...", "")
        .replace("\n\nMore details below ⬇️", "")
        .strip()
    )

    return " ".join([main_without_suffix] + replies).strip()


def build_publish_poster(session=None, available=True):
    poster = PosterMastodon.__new__(PosterMastodon)
    poster._session = session
    poster._is_available = available
    poster._auth_error = None
    return poster


class TestMastodonCaptionProperties:
    def setup_method(self):
        self.poster = PosterMastodon.__new__(PosterMastodon)

    @given(text=text_strategy, tags=tag_strategy)
    def test_all_parts_stay_under_mastodon_limit(self, text, tags):
        post = Post(text=text, tags=tags)

        main_caption, replies = self.poster._format_caption_thread(post)

        assert len(main_caption) <= MASTODON_CHARACTER_LIMIT
        assert all(len(reply) <= MASTODON_CHARACTER_LIMIT for reply in replies)

    @given(text=text_strategy, tags=long_tag_strategy)
    def test_splitting_with_tags_too_long(self, text, tags):
        post = Post(text=text, tags=tags)
        
        with pytest.raises(ValueError):
            self.poster._format_caption_thread(post)

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
    def test_reconstruction_preserves_uncapped_threads(self, text, tags):
        post = Post(text=text, tags=tags)

        main_caption, replies = self.poster._format_caption_thread(post)

        if len(replies) < MAX_REPLIES:
            reconstructed = reconstruct_text(main_caption, replies)
            assert reconstructed == text.strip()

    @given(pet=pet_strategy)
    def test_format_post_output_stays_under_mastodon_limit_after_splitting(self, pet):
        post = self.poster.format_post(pet)

        main_caption, replies = self.poster._format_caption_thread(post)

        assert len(main_caption) <= MASTODON_CHARACTER_LIMIT
        assert all(len(reply) <= MASTODON_CHARACTER_LIMIT for reply in replies)
        assert len(replies) <= MAX_REPLIES
    
    @given(
            text=caption_text,
            limit=st.integers(min_value=1, max_value=10),
           )
    def test_safe_truncate_correctly(self, text, limit):
        fst, snd = self.poster._safe_truncate(text, limit)

        assert len(fst) <= limit 

        if len(text) <= limit:
            assert fst == text
            assert snd == ""
        else:
            assert fst == fst.rstrip()
            assert snd == snd.strip()

    @given(
            text=st.text(),
            limit=st.integers(min_value=1, max_value=10),
            )
    def test_safe_truncate_nothing(self, text, limit):
        assume(len(text) <= limit)
        fst, snd = self.poster._safe_truncate(text, limit)


        assert fst == text
        assert snd == ""



class TestMastodonCaption:
    def setup_method(self):
        self.poster = PosterMastodon.__new__(PosterMastodon)

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

        reconstructed = reconstruct_text(main_caption, replies)

        assert len(replies) == MAX_REPLIES
        assert reconstructed != original_text
        assert replies[-1].endswith("...")

    def test_thread_preserves_original_text_content(self):
        original_text = " ".join(f"word{i}" for i in range(300))
        post = Post(text=original_text, tags=["AdoptDontShop", "Boston"])

        main_caption, replies = self.poster._format_caption_thread(post)

        reconstructed = reconstruct_text(main_caption, replies)

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

    def test_spaced_long_text_creates_reply(self):
        post = Post(text="x " * 1000, tags=["AdoptDontShop", "Boston"])

        main_caption, replies = self.poster._format_caption_thread(post)

        assert len(main_caption) <= MASTODON_CHARACTER_LIMIT
        assert main_caption.endswith("\n\n#AdoptDontShop #Boston")
        assert "..." in main_caption
        assert "More details below" in main_caption
        assert replies
        assert all(len(reply) <= MASTODON_CHARACTER_LIMIT for reply in replies)

    def test_unspaced_long_text_creates_reply(self):
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


class TestMastodonPublish:
    @pytest.mark.parametrize(
        (
            "available",
            "image_url",
            "authenticate_result",
            "auth_error",
            "expected_error",
        ),
        [
            (
                False,
                "https://example.com/pet.jpg",
                False,
                None,
                "Mastodon credentials not available.",
            ),
            (
                True,
                None,
                False,
                None,
                "Mastodon posts require an image URL.",
            ),
            (
                True,
                "https://example.com/pet.jpg",
                False,
                "RuntimeError: denied",
                "Mastodon authentication failed: RuntimeError: denied",
            ),
            (
                True,
                "https://example.com/pet.jpg",
                True,
                None,
                "Mastodon authentication did not create a session.",
            ),
        ],
    )
    def test_early_failure_logs_publish_result(
        self,
        caplog,
        available,
        image_url,
        authenticate_result,
        auth_error,
        expected_error,
    ):
        poster = build_publish_poster(available=available)
        poster._auth_error = auth_error
        poster.authenticate = Mock(return_value=authenticate_result)
        caplog.set_level(logging.INFO, logger="social_posters.mastodon")

        result = poster.publish(Post(text="Meet Poppy!", image_url=image_url))

        assert not result.success
        assert result.error_message == expected_error
        assert "Mastodon publish result:" in caplog.text
        assert expected_error in caplog.text

    def test_publish_logs_root_and_each_reply_output(self, caplog, tmp_path):
        image_path = tmp_path / "pet.jpg"
        image_path.write_bytes(b"image")
        session = Mock()
        session.media_post.return_value = {"id": "media-1"}
        session.status_post.side_effect = [
            {"id": "root-1", "url": "https://mastodon.example/root-1"},
            {"id": "reply-1"},
            {"id": "reply-2"},
        ]
        poster = build_publish_poster(session=session)
        poster._download_image = Mock(return_value=str(image_path))
        poster._format_caption_thread = Mock(
            return_value=("Main caption", ["First reply", "Second reply"])
        )
        caplog.set_level(logging.INFO, logger="social_posters.mastodon")

        result = poster.publish(
            Post(text="Original text", image_url="https://example.com/pet.jpg")
        )

        assert result.success
        assert result.post_id == "root-1"
        assert "kind=root reply_number=None" in caplog.text
        assert "kind=reply reply_number=1" in caplog.text
        assert "kind=reply reply_number=2" in caplog.text
        assert "'id': 'root-1'" in caplog.text
        assert "'id': 'reply-1'" in caplog.text
        assert "'id': 'reply-2'" in caplog.text
        assert (
            "Mastodon finished posting thread: root_id=root-1 reply_count=2"
            in caplog.text
        )
        assert session.status_post.call_args_list == [
            call("Main caption", media_ids=["media-1"]),
            call("First reply", in_reply_to_id="root-1"),
            call("Second reply", in_reply_to_id="root-1"),
        ]
        assert not image_path.exists()

    def test_partial_reply_failure_logs_completed_posts(self, caplog, tmp_path):
        image_path = tmp_path / "pet.jpg"
        image_path.write_bytes(b"image")
        session = Mock()
        session.media_post.return_value = {"id": "media-1"}
        session.status_post.side_effect = [
            {"id": "root-1", "url": "https://mastodon.example/root-1"},
            {"id": "reply-1"},
            RuntimeError("second reply failed"),
        ]
        poster = build_publish_poster(session=session)
        poster._download_image = Mock(return_value=str(image_path))
        poster._format_caption_thread = Mock(
            return_value=("Main caption", ["First reply", "Second reply"])
        )
        caplog.set_level(logging.INFO, logger="social_posters.mastodon")

        result = poster.publish(
            Post(text="Original text", image_url="https://example.com/pet.jpg")
        )

        assert not result.success
        assert result.error_message == "second reply failed"
        assert "'id': 'root-1'" in caplog.text
        assert "'id': 'reply-1'" in caplog.text
        assert "root_posted=True completed_reply_count=1" in caplog.text
        assert session.status_post.call_args_list == [
            call("Main caption", media_ids=["media-1"]),
            call("First reply", in_reply_to_id="root-1"),
            call("Second reply", in_reply_to_id="root-1"),
        ]
        assert not image_path.exists()
