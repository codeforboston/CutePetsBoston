from datetime import datetime
from typing import Optional
import os

import requests

from abstractions import Post, PostResult, SocialPoster


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
            return bool(self._access_token and self._did)
        except Exception:
            self._access_token = None
            self._did = None
            return False

    def publish(self, post: Post) -> PostResult:
        if not self._is_available:
            return PostResult(
                success=False,
                error_message="Bluesky credentials not available."
            )

        if not self._access_token or not self._did:
            if not self.authenticate():
                return PostResult(
                    success=False, error_message="Bluesky authentication failed."
                )

        headers = {"Authorization": f"Bearer {self._access_token}"}
        image_blob = None

        if post.image_url:
            try:
                img_response = requests.get(post.image_url, timeout=20)
                img_response.raise_for_status()
                upload = requests.post(
                    "https://bsky.social/xrpc/com.atproto.repo.uploadBlob",
                    headers={**headers, "Content-Type": "image/jpeg"},
                    data=img_response.content,
                    timeout=30,
                )
                upload.raise_for_status()
                image_blob = upload.json().get("blob")
            except Exception as exc:
                return PostResult(success=False, error_message=str(exc))

        text, facets = self._build_text_and_facets(post)
        record = {
            "$type": "app.bsky.feed.post",
            "text": text,
            "createdAt": datetime.utcnow().isoformat() + "Z",
        }

        if facets:
            record["facets"] = facets

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

        try:
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
            return PostResult(
                success=True,
                post_id=data.get("cid"),
                post_url=data.get("uri"),
            )
        except Exception as exc:
            return PostResult(success=False, error_message=str(exc))

    def format_post(self, pet):
        from abstractions import Post

        name = pet.name.split("*")[0].strip()

        text = f"Hi, I'm {name}! I'm a {pet.breed} looking for a forever home"
        if pet.location:
            text += f" in {pet.location}"
        text += "."

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

        if pet.pet_id:
            text += f"\n\nPet ID: {pet.pet_id}"

        species_tag = "DogsOfBluesky" if pet.species == "dog" else "CatsOfBluesky"
        tags = ["AdoptDontShop", "Boston", species_tag]

        return Post(
            text=text,
            image_url=pet.image_url,
            link=pet.adoption_url,
            alt_text=f"Photo of {name}, a {pet.breed} available for adoption",
            tags=tags,
        )
    def _build_text_and_facets(self, post: Post) -> tuple[str, list]:
        body = post.text
        facets = []

        if not post.tags:
            return body[:300], facets

        tag_strings = [f"#{tag}" for tag in post.tags if tag]
        tags_section = " ".join(tag_strings)
        separator = "\n\n"

        # Truncate body so the full text (body + separator + tags) fits in 300 chars.
        max_body = 300 - len(separator) - len(tags_section)
        full_text = f"{body[:max_body]}{separator}{tags_section}"

        # Compute byte offsets (AT Protocol facets use UTF-8 byte positions).
        encoded = full_text.encode("utf-8")
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

        return full_text, facets

