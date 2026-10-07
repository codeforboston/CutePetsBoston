from __future__ import annotations

import logging
import os
import pprint
import re
import tempfile
from urllib.parse import urlparse

import requests
from mastodon import Mastodon

from abstractions import AdoptablePet, Post, PostResult, SocialPoster
from abstractions import CITY_NAME, CITY_STATE

LINK_SUFFIX = "\n\nMore details at link 🔗"
MASTODON_CHARACTER_LIMIT = 500
TRUNCATION_SUFFIX = "..."
SENTENCE_END_RE = re.compile(r"[.!?]\s")

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

        photo_urls = post.selected_image_urls
        if not photo_urls:
            logger.warning("Mastodon posts require an image URL.")
            result = PostResult(
                success=False,
                error_message="Mastodon posts require an image URL.",
            )
            logger.info("Mastodon publish result: %s", pprint.pformat(result))
            return result
        logger.info("Mastodon post has %d photo URLs", len(photo_urls))

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

        stage = "preparing publish"

        try:
            stage = "preparing media"
            media_ids = []
            for index, image_url in enumerate(photo_urls, start=1):
                try:
                    media_ids.append(self._upload_media(session, post, image_url, index))
                except Exception as exc:
                    logger.warning("Mastodon image %d skipped: %s", index, exc)
            if not media_ids:
                raise RuntimeError("No usable Mastodon images.")

            stage = "formatting caption"
            logger.info("Mastodon formatting caption")
            caption = self._format_caption(post)
            logger.info("Mastodon caption output: length=%d", len(caption))
            logger.info("Mastodon caption: %s", pprint.pformat(caption))

            stage = "posting status"
            logger.info(
                "Mastodon posting status input: caption_length=%d media_ids=%s",
                len(caption),
                media_ids,
            )
            status = session.status_post(
                caption,
                media_ids=media_ids,
            )
            logger.info("Mastodon status post output: %s", pprint.pformat(status))

            result = PostResult(
                success=True,
                post_id=str(status["id"]),
                post_url=status.get("url"),
            )
            logger.info("Mastodon publish result: %s", pprint.pformat(result))
            return result

        except Exception as exc:
            logger.exception(
                "Mastodon posting failed during %s: %s",
                stage,
                exc,
            )
            result = PostResult(success=False, error_message=str(exc))
            logger.info("Mastodon publish result: %s", pprint.pformat(result))
            return result

        finally:
            self._session = None

    def _format_caption(self, post: Post) -> str:
        caption_text = post.text.strip()
        tag_suffix = self._format_tag_suffix(post.tags)

        if self._fits_single_post(caption_text, tag_suffix):
            return f"{caption_text}{tag_suffix}"

        link_suffix = LINK_SUFFIX if post.link else ""

        main_limit = self._main_caption_limit(link_suffix, tag_suffix)

        if main_limit <= 0:
            raise ValueError("Tags are too long to fit in a Mastodon post.")

        main_text, _ = self._safe_truncate(caption_text, main_limit)

        return f"{main_text}{TRUNCATION_SUFFIX}{link_suffix}{tag_suffix}"

    @staticmethod
    def _fits_single_post(caption_text: str, tag_suffix: str) -> bool:
        return len(caption_text) + len(tag_suffix) <= MASTODON_CHARACTER_LIMIT

    @staticmethod
    def _format_tag_suffix(tags: list[str]) -> str:
        clean_tags = [tag for tag in tags if tag]
        tag_text = " ".join(f"#{tag}" for tag in clean_tags)
        return f"\n\n{tag_text}" if tag_text else ""

    @staticmethod
    def _main_caption_limit(link_suffix: str, tag_suffix: str) -> int:
        return (
            MASTODON_CHARACTER_LIMIT
            - len(link_suffix)
            - len(tag_suffix)
            - len(TRUNCATION_SUFFIX)
        )

    def _download_image(self, image_url: str) -> str:
        parsed_url = urlparse(image_url)
        ext = os.path.splitext(parsed_url.path)[1] or ".jpg"

        with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
            try:
                with requests.get(image_url, stream=True, timeout=20) as response:
                    response.raise_for_status()

                    for chunk in response.iter_content(chunk_size=1024 * 128):
                        if chunk:
                            tmp.write(chunk)
            except Exception:
                os.unlink(tmp.name)
                raise
            return tmp.name

    def _upload_media(
        self, session: Mastodon, post: Post, image_url: str | None = None, index: int = 1
    ) -> str:
        image_url = image_url or (post.selected_image_urls[0] if post.selected_image_urls else None)
        if not image_url:
            raise ValueError("Mastodon posts require an image URL.")

        image_path = None
        try:
            logger.info("Start downloading image")
            logger.info(
                "Mastodon download image input: image_url=%s",
                image_url,
            )
            image_path = self._download_image(image_url)
            logger.info("Finish downloading image: image_path=%s", image_path)

            media_description = f"{post.alt_text or 'Photo of an adoptable pet'} (photo {index})"
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

        cut = -1
        for match in SENTENCE_END_RE.finditer(text[:limit]):
            cut = match.start() + 1

        if cut == -1:
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

        photos = pet.image_urls
        post = Post(
            text=text,
            image_urls=photos,
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
