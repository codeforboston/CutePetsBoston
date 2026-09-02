from datetime import datetime
import logging
import os
import pprint

import requests

from abstractions import Post, PostResult, SocialPoster
from config import CITY_HASHTAGS, CITY_NAME, CITY_STATE

logger = logging.getLogger(__name__)


class PosterBluesky(SocialPoster):
    def __init__(self):
        # Handle environment variable validation internally
        self.username = os.environ.get("BLUESKY_HANDLE")
        self.password = os.environ.get("BLUESKY_PASSWORD")
        self._access_token = None
        self._did = None  # Decentralized identifier from the Bluesky session.
        self._is_available = bool(self.username and self.password)

    @property
    def platform_name(self) -> str:
        return "Bluesky"

    def authenticate(self) -> bool:
        logger.info("Start authenticating to Bluesky")
        try:
            response = requests.post(
                "https://bsky.social/xrpc/com.atproto.server.createSession",
                json={"identifier": self.username, "password": self.password},
                timeout=20,
            )
            response.raise_for_status()
            session = response.json()
            self._access_token = session.get("accessJwt")
            self._did = session.get("did")
            ok = bool(self._access_token and self._did)
            if ok:
                logger.info("Bluesky authentication succeeded (did present=%s)", bool(self._did))
            else:
                logger.warning("Bluesky auth response missing accessJwt or did")
            return ok
        except Exception:
            logger.exception("Bluesky authentication failed")
            self._access_token = None
            self._did = None
            return False

    def publish(self, post: Post) -> PostResult:
        logger.info("Start publishing to Bluesky")
        logger.info("Bluesky post input: %s", pprint.pformat(post))

        if not self._is_available:
            logger.warning("Bluesky credentials not available.")
            result = PostResult(
                success=False,
                error_message="Bluesky credentials not available."
            )
            logger.info("Bluesky publish result: %s", pprint.pformat(result))
            return result

        if not self._access_token or not self._did:
            logger.info("No active Bluesky session; authenticating now")
            if not self.authenticate():
                result = PostResult(
                    success=False, error_message="Bluesky authentication failed."
                )
                logger.info("Bluesky publish result: %s", pprint.pformat(result))
                return result

        headers = {"Authorization": f"Bearer {self._access_token}"}
        image_blob = None

        if post.image_url:
            logger.info("Bluesky image URL found; starting download/upload")
            try:
                img_response = requests.get(post.image_url, timeout=20)
                img_response.raise_for_status()
                logger.info("Bluesky image downloaded (%d bytes)", len(img_response.content))

                upload = requests.post(
                    "https://bsky.social/xrpc/com.atproto.repo.uploadBlob",
                    headers={**headers, "Content-Type": "image/jpeg"},
                    data=img_response.content,
                    timeout=30,
                )
                upload.raise_for_status()
                image_blob = upload.json().get("blob")
                logger.info("Bluesky image uploaded (blob present=%s)", bool(image_blob))
            except Exception as exc:
                logger.exception("Bluesky image download/upload failed")
                result = PostResult(success=False, error_message=str(exc))
                logger.info("Bluesky publish result: %s", pprint.pformat(result))
                return result
        else:
            logger.info("Bluesky post has no image URL; publishing text-only post")

        logger.info("Building Bluesky text and facets")
        text, facets = self._build_text_and_facets(post)
        logger.info("Built text/facets (text_len=%d, facets_count=%d)", len(text), len(facets))
        logger.debug("Bluesky text preview: %s", text[:280])
        logger.debug("Bluesky facets: %s", pprint.pformat(facets))

        record = {
            "$type": "app.bsky.feed.post",
            "text": text,
            "createdAt": datetime.utcnow().isoformat() + "Z",
        }
        logger.debug("Bluesky record base: %s", pprint.pformat(record))

        if facets:
            record["facets"] = facets
            logger.info("Attached facets to Bluesky record")

        if image_blob:
            record["embed"] = {
                "$type": "app.bsky.embed.images",
                "images": [
                    {
                        "alt": post.alt_text or "Adoptable pet",
                        "image": image_blob,
                    }
                ],
            }
            logger.info("Attached image embed to Bluesky record")

        logger.debug("Final Bluesky record payload: %s", pprint.pformat(record))

        try:
            logger.info("Sending Bluesky createRecord request")
            response = requests.post(
                "https://bsky.social/xrpc/com.atproto.repo.createRecord",
                headers=headers,
                json={
                    "repo": self._did,
                    "collection": "app.bsky.feed.post",
                    "record": record,
                },
                timeout=30,
            )
            response.raise_for_status()
            data = response.json()
            result = PostResult(
                success=True,
                post_id=data.get("cid"),
                post_url=data.get("uri"),
            )
            logger.info("Bluesky createRecord succeeded")
            logger.info("Bluesky publish result: %s", pprint.pformat(result))
            return result
        except Exception as exc:
            logger.exception("Bluesky createRecord failed")
            result = PostResult(success=False, error_message=str(exc))
            logger.info("Bluesky publish result: %s", pprint.pformat(result))
            return result

    def format_post(self, pet):
        from abstractions import Post

        name = pet.name.split("*")[0].strip()

        text = f"Hi, I'm {name}! I'm a {pet.breed} looking for a forever home"
        if pet.location:
            text += f" in {pet.location}"
        text += "."

        city = ""
        if pet.location != f"{CITY_NAME}, {CITY_STATE}":
            city = pet.location.split(",")[0].capitalize()

        detail_parts = []
        if pet.age_string:
            detail_parts.append(pet.age_string)
        if pet.sex:
            detail_parts.append(pet.sex)
        if pet.size_group:
            detail_parts.append(f"{pet.size_group} size")
        details = " · ".join(detail_parts)

        if details:
            text += f"\n\n{details}"
        elif pet.description:
            text += f"\n\n{pet.description[:120]}"

        if pet.adoption_url:
            text += f"\n\nLearn more and adopt me: {pet.adoption_url}"

        species_tag = "DogsOfBluesky" if pet.species == "dog" else "CatsOfBluesky"
        tags = ["AdoptDontShop", *CITY_HASHTAGS, city, species_tag]

        return Post(
            text=text,
            image_url=pet.image_url,
            link=pet.adoption_url,
            alt_text=f"Photo of {name}, a {pet.breed} available for adoption",
            tags=tags,
        )

    def _build_text_and_facets(self, post: Post) -> tuple[str, list]:
        body = post.text
        facets: list = []
        separator = "\n\n"
        limit = 300

        tag_strings = [f"#{tag}" for tag in (post.tags) if tag]
        tags_section = " ".join(tag_strings)
        # Truncate body so the full text (body + separators + tags) fits in limit chars.
        max_body = limit - (len(separator) + len(tags_section) if tags_section else 0)
        # When the link URL is embedded in the body and would be truncated,
        # keep the full URL and trim text before it instead.
        if post.link and post.link in body:
            truncated_body = self._truncate_body_preserving_link(
                body,
                post.link,
                max_body,
            )
        else:
            truncated_body = body[:max_body]
        full_text = f"{truncated_body}{separator}{tags_section}" if tags_section else truncated_body

        encoded = full_text.encode("utf-8")

        if post.link:
            link_bytes = post.link.encode("utf-8")
            link_idx = encoded.find(link_bytes)
            if link_idx != -1:
                facets.append({
                    "index": {
                        "byteStart": link_idx,
                        "byteEnd": link_idx + len(link_bytes),
                    },
                    "features": [
                        {"$type": "app.bsky.richtext.facet#link", "uri": post.link}
                    ],
                })

        search_from = 0
        for tag_str in tag_strings:
            tag_bytes = tag_str.encode("utf-8")
            idx = encoded.find(tag_bytes, search_from)
            if idx != -1:
                facets.append({
                    "index": {"byteStart": idx, "byteEnd": idx + len(tag_bytes)},
                    "features": [{"$type": "app.bsky.richtext.facet#tag", "tag": tag_str[1:]}],
                })
                search_from = idx + len(tag_bytes)

        facets.sort(key=lambda f: f["index"]["byteStart"])
        return full_text, facets

    @staticmethod
    def _truncate_body_preserving_link(body: str, link: str, limit: int) -> str:
        if len(body) <= limit:
            return body

        link_pos = body.find(link)
        if link_pos == -1:
            return body[:limit]

        link_end = link_pos + len(link)
        if link_end <= limit:
            return body[:limit]

        if len(link) > limit:
            return body[:limit]

        prefix = body[:link_pos].rstrip()
        separator = " " if prefix else ""
        prefix_limit = limit - len(link) - len(separator)

        if prefix_limit <= 0:
            return link

        trimmed_prefix = prefix[:prefix_limit].rstrip()
        if len(prefix) > prefix_limit:
            line_start = trimmed_prefix.rfind("\n")
            clean_prefix = trimmed_prefix[:line_start].rstrip() if line_start != -1 else ""
            if clean_prefix:
                trimmed_prefix = clean_prefix

        separator = " " if trimmed_prefix else ""
        return f"{trimmed_prefix}{separator}{link}"

