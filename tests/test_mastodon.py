import logging
from unittest.mock import Mock, call

from abstractions import AdoptablePet, Post
from hypothesis import given, strategies as st, assume
import pytest
from social_posters.mastodon import (
    PosterMastodon,
    MASTODON_CHARACTER_LIMIT,
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
    image_urls=st.just(["https://example.com/image.jpg"]),
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


def build_publish_poster(session=None, available=True):
    poster = PosterMastodon.__new__(PosterMastodon)
    poster._session = session
    poster._is_available = available
    poster._auth_error = None
    return poster


class TestMastodonConfiguration:
    def test_does_not_fall_back_to_test_token(self, monkeypatch):
        monkeypatch.delenv("MASTODON_TOKEN", raising=False)
        monkeypatch.setenv("MASTODON_TEST_TOKEN", "test-token")

        poster = PosterMastodon()

        assert poster.token is None
        assert poster._is_available is False


class TestMastodonCaptionProperties:
    def setup_method(self):
        self.poster = PosterMastodon.__new__(PosterMastodon)

    @given(text=text_strategy, tags=tag_strategy)
    def test_all_parts_stay_under_mastodon_limit(self, text, tags):
        post = Post(text=text, tags=tags)

        caption = self.poster._format_caption(post)

        assert len(caption) <= MASTODON_CHARACTER_LIMIT

    @given(text=text_strategy, tags=long_tag_strategy)
    def test_splitting_with_tags_too_long(self, text, tags):
        post = Post(text=text, tags=tags)
        
        with pytest.raises(ValueError):
            self.poster._format_caption(post)

    @given(text=text_strategy, tags=tag_strategy)
    def test_caption_never_includes_link_suffix_when_link_missing(self, text, tags):
        post = Post(text=text, tags=tags)

        caption = self.poster._format_caption(post)

        assert "More details at link" not in caption

    @given(text=text_strategy, tags=tag_strategy)
    def test_caption_with_link_includes_link_suffix(self, text, tags):
        post = Post(text=text, link="https://example.com/pet", tags=tags)

        caption = self.poster._format_caption(post)

        tag_suffix = "\n\n" + " ".join(f"#{tag}" for tag in tags if tag)
        if len(text.strip()) + len(tag_suffix) > MASTODON_CHARACTER_LIMIT:
            assert "More details at link 🔗" in caption
        else:
            assert "More details at link 🔗" not in caption

    @given(pet=pet_strategy)
    def test_format_post_output_stays_under_mastodon_limit(self, pet):
        post = self.poster.format_post(pet)

        caption = self.poster._format_caption(post)

        assert len(caption) <= MASTODON_CHARACTER_LIMIT
    
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

    def test_no_tags(self):
        post = Post(text="Hello, world!")

        caption = self.poster._format_caption(post)

        assert caption == "Hello, world!"

    def test_with_tags(self):
        post = Post(text="Meet Poppy!", tags=["AdoptDontShop", "Boston"])

        caption = self.poster._format_caption(post)

        assert caption == "Meet Poppy!\n\n#AdoptDontShop #Boston"

    def test_empty_tags_are_ignored(self):
        post = Post(text="Meet Poppy!", tags=["AdoptDontShop", "", None, "Boston"])

        caption = self.poster._format_caption(post)

        assert caption == "Meet Poppy!\n\n#AdoptDontShop #Boston"

    def test_long_text_without_link_skips_link_suffix(self):
        post = Post(text="x" * 1000, tags=["AdoptDontShop", "Boston"])

        caption = self.poster._format_caption(post)

        assert len(caption) <= MASTODON_CHARACTER_LIMIT
        assert caption.endswith("\n\n#AdoptDontShop #Boston")
        assert "..." in caption
        assert "More details at link" not in caption

    def test_long_unspaced_text_is_truncated_to_single_post(self):
        post = Post(text="x" * 1000, tags=["AdoptDontShop", "Boston"])

        caption = self.poster._format_caption(post)

        assert len(caption) <= MASTODON_CHARACTER_LIMIT
        assert "..." in caption
        assert "\n\n#AdoptDontShop #Boston" in caption

    def test_long_text_with_link_gets_link_suffix(self):
        post = Post(
            text="word " * 400,
            link="https://example.com/adopt-me",
            tags=["AdoptDontShop", "Boston"],
        )

        caption = self.poster._format_caption(post)

        assert len(caption) <= MASTODON_CHARACTER_LIMIT
        assert "More details at link 🔗" in caption
        assert caption.endswith("\n\n#AdoptDontShop #Boston")
        assert "https://example.com/adopt-me" not in caption

    def test_long_text_without_tags_is_truncated(self):
        post = Post(text="hello " * 300)

        caption = self.poster._format_caption(post)

        assert len(caption) <= MASTODON_CHARACTER_LIMIT
        assert "..." in caption

    def test_long_text_with_sentence_end_truncates_at_sentence_boundary(self):
        long_text = "First sentence here. " * 30
        post = Post(text=long_text, link="https://example.com/adopt-me")

        caption = self.poster._format_caption(post)

        assert len(caption) <= MASTODON_CHARACTER_LIMIT
        assert "..." in caption
        assert caption.index("...") > len("First sentence here. First sentence here.")
        assert "... First" not in caption

    def test_safe_truncate_does_not_split_words_when_possible(self):
        kept, remaining = self.poster._safe_truncate("hello world again", 12)

        assert kept == "hello world"
        assert remaining == "again"

    def test_safe_truncate_cuts_at_sentence_boundary_when_available(self):
        kept, remaining = self.poster._safe_truncate("One. Two words", 7)

        # The word-boundary cut would keep "One. Two", breaking mid-sentence.
        assert kept == "One."
        assert remaining == "Two words"

    def test_safe_truncate_prefers_last_sentence_boundary_before_limit(self):
        kept, remaining = self.poster._safe_truncate(
            "First. Second. Third sentence continues here", 20
        )

        assert kept == "First. Second."
        assert remaining == "Third sentence continues here"

    def test_safe_truncate_falls_back_when_no_complete_sentence_fits(self):
        kept, remaining = self.poster._safe_truncate("sentence ends. tail", 14)

        assert kept == "sentence"
        assert remaining == "ends. tail"


class TestMastodonPublish:
    def test_upload_media_cleans_up_file_when_upload_fails(self, tmp_path):
        image_path = tmp_path / "pet.jpg"
        image_path.write_bytes(b"image")
        session = Mock()
        session.media_post.side_effect = RuntimeError("upload failed")
        poster = PosterMastodon.__new__(PosterMastodon)
        poster._download_image = Mock(return_value=str(image_path))

        with pytest.raises(RuntimeError, match="upload failed"):
            poster._upload_media(
                session,
                Post(text="Meet Poppy!", image_urls=["https://example.com/pet.jpg"]),
            )

        assert not image_path.exists()

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

        result = poster.publish(Post(text="Meet Poppy!", image_urls=[image_url] if image_url else []))

        assert not result.success
        assert result.error_message == expected_error
        assert "Mastodon publish result:" in caplog.text
        assert expected_error in caplog.text

    def test_publish_posts_single_status(self, caplog, tmp_path):
        image_path = tmp_path / "pet.jpg"
        image_path.write_bytes(b"image")
        session = Mock()
        session.media_post.return_value = {"id": "media-1"}
        session.status_post.return_value = {
            "id": "status-1",
            "url": "https://mastodon.example/status-1",
        }
        poster = build_publish_poster(session=session)
        poster._download_image = Mock(return_value=str(image_path))
        poster._format_caption = Mock(return_value="Single caption")
        caplog.set_level(logging.INFO, logger="social_posters.mastodon")

        result = poster.publish(
            Post(
                text="Original text",
                image_urls=["https://example.com/pet.jpg"],
                link="https://example.com/adopt",
            )
        )

        assert result.success
        assert result.post_id == "status-1"
        assert "'id': 'status-1'" in caplog.text
        assert (
            session.status_post.call_args_list == [
                call("Single caption", media_ids=["media-1"]),
            ]
        )
        assert not image_path.exists()

    def test_status_post_failure_logs_publish_result(self, caplog, tmp_path):
        image_path = tmp_path / "pet.jpg"
        image_path.write_bytes(b"image")
        session = Mock()
        session.media_post.return_value = {"id": "media-1"}
        session.status_post.side_effect = RuntimeError("status failed")
        poster = build_publish_poster(session=session)
        poster._download_image = Mock(return_value=str(image_path))
        poster._format_caption = Mock(return_value="Single caption")
        caplog.set_level(logging.INFO, logger="social_posters.mastodon")

        result = poster.publish(
            Post(text="Original text", image_urls=["https://example.com/pet.jpg"])
        )

        assert not result.success
        assert result.error_message == "status failed"
        assert "Mastodon posting failed during posting status" in caplog.text
        assert not image_path.exists()
