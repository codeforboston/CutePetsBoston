from __future__ import annotations

import os
import tempfile
from urllib.parse import urlparse

import requests
from mastodon import Mastodon

from abstractions import AdoptablePet, Post, PostResult, SocialPoster
from abstractions import CITY_NAME, CITY_STATE


THREAD_SUFFIX = "\n\nMore details below ⬇️"
MASTODON_CHARACTER_LIMIT = 500
TRUNCATION_SUFFIX = "..."
MAX_REPLIES = 5


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

    def _format_caption_thread(self, post: Post) -> tuple[str, list[str]]:
        caption_text = post.text.strip()
        tag_suffix = self._format_tag_suffix(post.tags)

        if self._fits_single_post(caption_text, tag_suffix):
            return f"{caption_text}{tag_suffix}", []

        main_limit = self._main_caption_limit(tag_suffix)

        if main_limit <= 0:
            raise ValueError("Tags are too long to fit in a Mastodon post.")

        main_text, overflow = self._safe_truncate(caption_text, main_limit)
        replies = self._split_reply_chunks(overflow)

        main_caption = (
            f"{main_text}"
            f"{TRUNCATION_SUFFIX}"
            f"{THREAD_SUFFIX}"
            f"{tag_suffix}"
        )

        return main_caption, replies

    @staticmethod
    def _fits_single_post(caption_text: str, tag_suffix: str) -> bool:
        return len(caption_text) + len(tag_suffix) <= MASTODON_CHARACTER_LIMIT

    @staticmethod
    def _format_tag_suffix(tags: list[str]) -> str:
        clean_tags = [tag for tag in tags if tag]
        tag_text = " ".join(f"#{tag}" for tag in clean_tags)
        return f"\n\n{tag_text}" if tag_text else ""

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