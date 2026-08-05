from __future__ import annotations

import logging
import os
import pprint
import tempfile
from collections.abc import Iterator
from urllib.parse import urlparse

import requests
from mastodon import Mastodon

from abstractions import AdoptablePet, Post, PostResult, SocialPoster
from abstractions import CITY_NAME, CITY_STATE

THREAD_SUFFIX = "\n\nMore details below ⬇️"
MASTODON_CHARACTER_LIMIT = 500
TRUNCATION_SUFFIX = "..."
MAX_REPLIES = 5

logger = logging.getLogger(__name__)


class PosterMastodon(SocialPoster):
    def __init__(self) -> None:
        raw_token = os.environ.get("MASTODON_TOKEN")
        self.token = raw_token.strip() if raw_token else None
        self.api_base_url = os.environ.get(
            "MASTODON_API_BASE_URL",
            "https://mastodon.social",
        )
        self._session: Mastodon | None = None
        self._is_available = bool(self.token)
        self._auth_error: str | None = None

    @property
    def platform_name(self) -> str:
        return "Mastodon"

    def authenticate(self) -> bool:
        logger.info("Start Authenticating to Mastodon")
        try:
            self._session = Mastodon(
                access_token=self.token,
                api_base_url=self.api_base_url,
            )
            self._session.account_verify_credentials()
            self._auth_error = None
        except Exception as exc:
            logger.exception(
                "Mastodon authentication failed"
            )
            self._session = None
            self._auth_error = f"{type(exc).__name__}: {exc}"
            return False
        else:
            logger.info(
                "Mastodon authentication succeeded"
            )
        return True

    def publish(self, post: Post) -> PostResult:
        logger.info("Start Publishing to Mastodon")
        logger.info("Mastodon post input: %s", pprint.pformat(post))
        if not self._is_available:
            logger.warning("Mastodon credentials not available.")
            result = PostResult(
                success=False,
                error_message="Mastodon credentials not available.",
            )
            logger.info("Mastodon publish result: %s", pprint.pformat(result))
            return result
        logger.info("Mastodon credentials available.")

        if not post.image_url:
            logger.warning("Mastodon posts require an image URL.")
            result = PostResult(
                success=False,
                error_message="Mastodon posts require an image URL.",
            )
            logger.info("Mastodon publish result: %s", pprint.pformat(result))
            return result
        logger.info("Mastodon posts have image URL")

        if self._session is None and not self.authenticate():
            logger.warning("Mastodon authentication failed.")
            result = PostResult(
                success=False,
                error_message=(
                    "Mastodon authentication failed."
                    if not self._auth_error
                    else f"Mastodon authentication failed: {self._auth_error}"
                ),
            )
            logger.info("Mastodon publish result: %s", pprint.pformat(result))
            return result

        session = self._session
        if session is None:
            logger.error("Mastodon authentication did not create a session.")
            result = PostResult(
                success=False,
                error_message="Mastodon authentication did not create a session.",
            )
            logger.info("Mastodon publish result: %s", pprint.pformat(result))
            return result
        logger.info("Mastodon authentication successful")
        
        root_status: dict | None = None
        completed_reply_count = 0
        stage = "preparing publish"

        try:
            stage = "preparing media"
            media_id = self._upload_media(session, post)

            stage = "formatting caption thread"
            logger.info("Mastodon formatting caption thread")
            main_caption, replies = self._format_caption_thread(post)
            main_caption_formatted = pprint.pformat(main_caption)
            replies_formatted = pprint.pformat(replies)
            logger.info(
                "Mastodon caption thread output: main_caption_length=%d reply_count=%d",
                len(main_caption),
                len(replies),
            )
            logger.info("Mastodon main caption: %s", main_caption_formatted)
            logger.info("Mastodon replies: %s", replies_formatted)
            
            stage = "posting thread"
            logger.info("Mastodon start posting thread")
            logger.info(
                "Mastodon posting thread input: main_caption_length=%d reply_count=%d media_id=%s",
                len(main_caption),
                len(replies),
                media_id,
            )
            for post_kind, reply_number, status in self._post_thread(
                session,
                main_caption,
                replies,
                media_id,
            ):
                if post_kind == "root":
                    root_status = status
                else:
                    completed_reply_count += 1

                logger.info(
                    "Mastodon thread post output: kind=%s reply_number=%s status=%s",
                    post_kind,
                    reply_number,
                    pprint.pformat(status),
                )

            if root_status is None:
                raise RuntimeError("Mastodon thread did not return a root status.")

            logger.info(
                "Mastodon finished posting thread: root_id=%s reply_count=%d",
                root_status["id"],
                completed_reply_count,
            )

            result = PostResult(
                success=True,
                post_id=str(root_status["id"]),
                post_url=root_status.get("url"),
            )
            logger.info("Mastodon publish result: %s", pprint.pformat(result))
            return result

        except Exception as exc:
            logger.exception(
                "Mastodon posting failed during %s: %s "
                "(root_posted=%s completed_reply_count=%d)",
                stage,
                exc,
                root_status is not None,
                completed_reply_count,
            )
            result = PostResult(success=False, error_message=str(exc))
            logger.info("Mastodon publish result: %s", pprint.pformat(result))
            return result

        finally:
            self._session = None

    def _post_thread(
        self,
        session: Mastodon,
        main_caption: str,
        replies: list[str],
        media_id: str,
    ) -> Iterator[tuple[str, int | None, dict]]:
        status = session.status_post(
            main_caption,
            media_ids=[media_id],
        )
        yield "root", None, status

        root_status_id = status["id"]

        for reply_number, reply_text in enumerate(replies, start=1):
            reply_status = session.status_post(
                reply_text,
                in_reply_to_id=root_status_id,
            )
            yield "reply", reply_number, reply_status

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

    def _upload_media(self, session: Mastodon, post: Post) -> str:
        if not post.image_url:
            raise ValueError("Mastodon posts require an image URL.")

        image_path = None
        try:
            logger.info("Start downloading image")
            logger.info(
                "Mastodon download image input: image_url=%s",
                post.image_url,
            )
            image_path = self._download_image(post.image_url)
            logger.info("Finish downloading image: image_path=%s", image_path)

            media_description = post.alt_text or "Photo of an adoptable pet"
            logger.info(
                "Mastodon media upload input: image_path=%s description=%s",
                image_path,
                media_description,
            )
            media = session.media_post(
                image_path,
                description=media_description,
            )
            logger.info("Mastodon uploaded media: %s", pprint.pformat(media))
            return str(media["id"])
        finally:
            if image_path and os.path.exists(image_path):
                os.unlink(image_path)

    @staticmethod
    def _safe_truncate(text: str, limit: int) -> tuple[str, str]:
        if len(text) <= limit:
            return text, ""

        cut = text.rfind(" ", 0, limit)

        if cut == -1:
            cut = limit

        return text[:cut].rstrip(), text[cut:].strip()

    def format_post(self, pet: AdoptablePet) -> Post:
        logger.info(
            "Mastodon formatting pet into post: name=%s species=%s breed=%s location=%s pet_id=%s",
            pet.name,
            pet.species,
            pet.breed,
            pet.location,
            pet.pet_id,
        )
        text = (
            f"Meet {pet.name}! This adorable {pet.breed} {pet.species} "
            f"is looking for a forever home in {pet.location}."
        )
        logger.info("Mastodon base post text: %s", text)

        if pet.adoption_url:
            text += f" Adopt {pet.name}: {pet.adoption_url}"
            logger.info("Mastodon post text after adoption URL: %s", text)

        if pet.description:
            text += f"\n\n{pet.description}"
            logger.info("Mastodon post text after description: %s", text)

        city = ""
        if pet.location != f"{CITY_NAME}, {CITY_STATE}":
            city = pet.location.split(",")[0].capitalize()
        logger.info("Mastodon derived city tag: %s", city)

        post = Post(
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
        logger.info("Mastodon formatted Post output: %s", pprint.pformat(post))
        return post
