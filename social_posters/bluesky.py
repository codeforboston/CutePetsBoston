from datetime import datetime
from typing import Optional
import os

import requests

from abstractions import Post, PostResult, SocialPoster


class PosterBluesky(SocialPoster):
    def __init__(self):
        # Handle environment variable validation internally
        self.username = (os.environ.get("BLUESKY_HANDLE") or
                        os.environ.get("BLUESKY_TEST_HANDLE"))
        self.password = (os.environ.get("BLUESKY_PASSWORD") or
                        os.environ.get("BLUESKY_TEST_PASSWORD"))
        self._access_token = None
        self._did = None  # Decentralized identifier from the Bluesky session.
        self._is_available = bool(self.username and self.password)

    @classmethod
    def create_if_available(cls) -> Optional['PosterBluesky']:
        """Create Bluesky poster if credentials are available in environment variables."""
        username = (os.environ.get("BLUESKY_HANDLE") or
                   os.environ.get("BLUESKY_TEST_HANDLE"))
        password = (os.environ.get("BLUESKY_PASSWORD") or
                   os.environ.get("BLUESKY_TEST_PASSWORD"))
        if username and password:
            return cls(username, password)
        return None

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

        record = {
            "$type": "app.bsky.feed.post",
            "text": self._format_text(post),
            "createdAt": datetime.utcnow().isoformat() + "Z",
        }

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

    def _format_text(self, post: Post) -> str:
        text = post.text
        if post.tags:
            tags = " ".join(f"#{tag}" for tag in post.tags if tag)
            text = f"{text}\n\n{tags}"
        return text[:300]
