import os
import tempfile
from dataclasses import dataclass, field
from urllib.parse import urlparse

import requests
from mastodon import Mastodon

from abstractions import AdoptablePet, Post, PostResult, SocialPoster
from abstractions import CITY_NAME, CITY_STATE

THREAD_SUFFIX = "\n\nMore details below ⬇️"
MASTODON_CHARACTER_LIMIT = 500
TRUNCATION_SUFFIX = "..."
MAX_REPLIES = 5

"""
Mastodon implementation of the Cute Pets Boston Project
Requires: MASTODON_TOKEN for authentication

The domain that hosts our account (Mastodon.social) has 
a 500 chars limit, we prioritize the adoption link at
the top of the post by overriding format_post, then 
split the exceeding chars into the replies section 
with number of replies capped at the MAX_REPLIES. If post
content does not exceed limit, no replies generated. If
replies exceed MAX_REPLIES, truncate it with `...` . Replies
are text-only and no media attached.

Use the preview file within manual_testing folder to inspect 
each phase of the pipeline when developing or debugging 
Mastodon due to its complexity from split text. There, 
you can choose to inspect only the pet, the formatted
post, the main post, the replies, or the trace itself that
contains the properties of the post. Use safe truncation to
prevent cutting off words when splitting text. Use 
_format_caption_thread_with_trace to create split text with
trace.

Pipeline: AdoptablePet => format_post (override formatting) =>
_format_caption_thread_with_trace(Mastodon splitting) => 
publish main status => publish replies (if needed) => PostResult
"""
@dataclass
class MastodonFormatTrace:
    raw_text: str
    caption_text: str
    tags: list[str]
    tag_suffix: str
    main_limit: int | None = None
    main_text: str | None = None
    overflow: str | None = None
    main_caption: str | None = None
    replies: list[str] = field(default_factory=list)
    was_split: bool = False
    was_capped: bool = False


class PosterMastodon(SocialPoster):
    def __init__(self) -> None:
        raw_token = os.environ.get("MASTODON_TOKEN")
        self.token = raw_token.strip() if raw_token else None
        self.api_base_url = "https://mastodon.social"
        self._session: Mastodon | None = None
        self._is_available = bool(self.token)
        self._auth_error: str | None = None

    @property
    def platform_name(self) -> str:
        return "Mastodon"

    def authenticate(self) -> bool:
        try:
            self._session = Mastodon(
                access_token=self.token,
                api_base_url=self.api_base_url,
            )
            self._session.account_verify_credentials()
            self._auth_error = None
            return True
        except Exception as exc:
            self._session = None
            self._auth_error = f"{type(exc).__name__}: {exc}"
            return False

    def publish(self, post: Post) -> PostResult:
        error = self._ensure_ready_to_publish(post)
        if error:
            return error

        image_path = None

        try:
            image_path = self._download_image(post.image_url)

            media = self._session.media_post(
                image_path,
                description=post.alt_text or "Photo of an adoptable pet",
            )

            main_caption, replies = self._format_caption_thread(post)
            status = self._post_thread(main_caption, replies, media["id"])

            return PostResult(
                success=True,
                post_id=str(status["id"]),
                post_url=status.get("url"),
            )

        except Exception as exc:
            return PostResult(success=False, error_message=str(exc))

        finally:
            self._session = None
            if image_path and os.path.exists(image_path):
                os.unlink(image_path)

    def _ensure_ready_to_publish(self, post: Post) -> PostResult | None:
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
                error_message=(
                    "Mastodon authentication failed."
                    if not self._auth_error
                    else f"Mastodon authentication failed: {self._auth_error}"
                ),
            )

        return None

    def _post_thread(
        self,
        main_caption: str,
        replies: list[str],
        media_id: str,
    ) -> dict:
        status = self._session.status_post(
            main_caption,
            media_ids=[media_id],
        )

        root_status_id = status["id"]

        for reply_text in replies:
            self._session.status_post(
                reply_text,
                in_reply_to_id=root_status_id,
            )

        return status

    def _format_caption_thread_with_trace(
        self,
        post: Post,
    ) -> tuple[str, list[str], MastodonFormatTrace]:
        caption_text, tag_suffix, trace = self._prepare_caption(post)

        if self._fits_single_post(caption_text, tag_suffix):
            return self._build_single_post(caption_text, tag_suffix, trace)

        main_limit = self._validated_main_limit(tag_suffix)
        main_text, overflow = self._safe_truncate(caption_text, main_limit)
        replies = self._split_reply_chunks(overflow)
        main_caption = self._build_main_caption(main_text, tag_suffix)

        trace = self._finalize_trace(
            trace=trace,
            main_limit=main_limit,
            main_text=main_text,
            overflow=overflow,
            main_caption=main_caption,
            replies=replies,
        )

        return main_caption, replies, trace

    def _format_caption_thread(self, post: Post) -> tuple[str, list[str]]:
        main_caption, replies, _ = self._format_caption_thread_with_trace(post)
        return main_caption, replies

    def _prepare_caption(
        self,
        post: Post,
    ) -> tuple[str, str, MastodonFormatTrace]:
        tags, tag_suffix = self._format_tags(post.tags)
        caption_text = post.text.strip()

        trace = MastodonFormatTrace(
            raw_text=post.text,
            caption_text=caption_text,
            tags=tags,
            tag_suffix=tag_suffix,
        )

        return caption_text, tag_suffix, trace

    @staticmethod
    def _fits_single_post(caption_text: str, tag_suffix: str) -> bool:
        return len(caption_text) + len(tag_suffix) <= MASTODON_CHARACTER_LIMIT

    @staticmethod
    def _build_single_post(
        caption_text: str,
        tag_suffix: str,
        trace: MastodonFormatTrace,
    ) -> tuple[str, list[str], MastodonFormatTrace]:
        main_caption = f"{caption_text}{tag_suffix}"
        trace.main_caption = main_caption
        return main_caption, [], trace

    def _validated_main_limit(self, tag_suffix: str) -> int:
        main_limit = self._main_caption_limit(tag_suffix)

        if main_limit <= 0:
            raise ValueError("Tags are too long to fit in a Mastodon post.")

        return main_limit

    @staticmethod
    def _build_main_caption(main_text: str, tag_suffix: str) -> str:
        return (
            f"{main_text}"
            f"{TRUNCATION_SUFFIX}"
            f"{THREAD_SUFFIX}"
            f"{tag_suffix}"
        )

    @staticmethod
    def _finalize_trace(
        trace: MastodonFormatTrace,
        main_limit: int,
        main_text: str,
        overflow: str,
        main_caption: str,
        replies: list[str],
    ) -> MastodonFormatTrace:
        trace.main_limit = main_limit
        trace.main_text = main_text
        trace.overflow = overflow
        trace.replies = replies
        trace.main_caption = main_caption
        trace.was_split = True
        trace.was_capped = (
            replies[-1].endswith(TRUNCATION_SUFFIX)
            if replies
            else False
        )

        return trace

    @staticmethod
    def _format_tags(tags: list[str]) -> tuple[list[str], str]:
        clean_tags = [tag for tag in tags if tag]
        tag_text = " ".join(f"#{tag}" for tag in clean_tags)
        tag_suffix = f"\n\n{tag_text}" if tag_text else ""
        return clean_tags, tag_suffix

    @staticmethod
    def _main_caption_limit(tag_suffix: str) -> int:
        return (
            MASTODON_CHARACTER_LIMIT
            - len(tag_suffix)
            - len(THREAD_SUFFIX)
            - len(TRUNCATION_SUFFIX)
        )

    def _split_reply_chunks(self, text: str) -> list[str]:
        chunks = []
        remaining = text.strip()

        while remaining and len(chunks) < MAX_REPLIES:
            chunk, remaining = self._safe_truncate(
                remaining,
                MASTODON_CHARACTER_LIMIT,
            )
            chunks.append(chunk)

        if remaining and chunks:
            cutoff = MASTODON_CHARACTER_LIMIT - len(TRUNCATION_SUFFIX)
            last_chunk, _ = self._safe_truncate(chunks[-1], cutoff)
            chunks[-1] = f"{last_chunk}{TRUNCATION_SUFFIX}"

        return chunks

    def _download_image(self, image_url: str) -> str:
        parsed_url = urlparse(image_url)
        ext = os.path.splitext(parsed_url.path)[1] or ".jpg"

        with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
            with requests.get(image_url, stream=True, timeout=20) as response:
                response.raise_for_status()

                for chunk in response.iter_content(chunk_size=1024 * 128):
                    if chunk:
                        tmp.write(chunk)

            return tmp.name

    @staticmethod
    def _safe_truncate(text: str, limit: int) -> tuple[str, str]:
        if len(text) <= limit:
            return text, ""

        cut = text.rfind(" ", 0, limit)

        if cut == -1:
            cut = limit

        return text[:cut].rstrip(), text[cut:].strip()

    def format_post(self, pet: AdoptablePet) -> Post:
        text = (
            f"Meet {pet.name}! This adorable {pet.breed} {pet.species} "
            f"is looking for a forever home in {pet.location}."
        )

        if pet.adoption_url:
            text += f" Adopt {pet.name}: {pet.adoption_url}"

        if pet.description:
            text += f"\n\n{pet.description}"

        city = ""
        if pet.location != f"{CITY_NAME}, {CITY_STATE}":
            city = pet.location.split(",")[0].capitalize()

        return Post(
            text=text,
            image_url=pet.image_url,
            link=pet.adoption_url,
            alt_text=(
                f"Photo of {pet.name}, a {pet.breed} {pet.species} "
                "available for adoption"
            ),
            tags=[
                "adoptdontshop",
                "rescue",
                city,
                pet.species,
                pet.breed.lower().replace(" ", ""),
            ],
        )