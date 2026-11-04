"""Official API adapters. Reading an inbox never calls the reply methods."""

import html
import os
import re
from datetime import datetime, timezone

import requests

from abstractions import PostResult
from database import PublishedPost
from social_posters.bluesky import PosterBluesky
from social_posters.instagram import GRAPH_API_BASE
from social_replies.models import Comment


def get_json(url: str, **kwargs) -> dict:
    response = requests.get(url, timeout=25, **kwargs)
    response.raise_for_status()
    return response.json()


class BlueskyReplies:
    platform_name = "Bluesky"

    def read(self, post: PublishedPost) -> list[Comment]:
        uri = post.get("post_url")
        if not uri or not uri.startswith("at://"):
            raise ValueError("Bluesky post is missing its AT URI")
        tree = get_json(
            "https://public.api.bsky.app/xrpc/app.bsky.feed.getPostThread",
            params={"uri": uri, "depth": 2, "parentHeight": 0},
        )["thread"]
        root = tree["post"]
        own_id = root["author"]["did"]
        comments = []
        for node in tree.get("replies", []):
            reply = node.get("post")
            if not reply:
                continue
            author = reply["author"]
            record = reply["record"]
            if record.get("reply", {}).get("parent", {}).get("uri") != uri:
                continue
            comments.append(
                Comment(
                    platform=self.platform_name,
                    comment_id=reply["uri"],
                    root_id=uri,
                    author_id=author["did"],
                    author=author["handle"],
                    text=record["text"],
                    created_at=record["createdAt"],
                    url=f"https://bsky.app/profile/{author['did']}/post/{reply['uri'].rsplit('/', 1)[-1]}",
                    is_own=author["did"] == own_id,
                    answered=any(
                        child.get("post", {}).get("author", {}).get("did") == own_id
                        for child in node.get("replies", [])
                    ),
                    context={"root_cid": root["cid"], "parent_cid": reply["cid"]},
                )
            )
        return comments

    def reply(self, comment: Comment, text: str) -> PostResult:
        poster = PosterBluesky()
        if not poster.authenticate():
            return PostResult(success=False, error_message="Bluesky authentication failed")
        response = requests.post(
            "https://bsky.social/xrpc/com.atproto.repo.createRecord",
            headers={"Authorization": f"Bearer {poster._access_token}"},
            json={
                "repo": poster._did,
                "collection": "app.bsky.feed.post",
                "record": {
                    "$type": "app.bsky.feed.post",
                    "text": text,
                    "createdAt": datetime.now(timezone.utc).isoformat(),
                    "reply": {
                        "root": {"uri": comment.root_id, "cid": comment.context["root_cid"]},
                        "parent": {"uri": comment.comment_id, "cid": comment.context["parent_cid"]},
                    },
                },
            },
            timeout=25,
        )
        response.raise_for_status()
        return PostResult(success=True, post_id=response.json()["uri"])


class MastodonReplies:
    platform_name = "Mastodon"

    def __init__(self) -> None:
        self.base = os.environ.get("MASTODON_API_BASE_URL", "https://mastodon.social").rstrip("/")

    def read(self, post: PublishedPost) -> list[Comment]:
        post_id = post["post_id"]
        root = get_json(f"{self.base}/api/v1/statuses/{post_id}")
        own_id = root["account"]["id"]
        descendants = get_json(f"{self.base}/api/v1/statuses/{post_id}/context")["descendants"]
        comments = []
        for reply in descendants:
            if str(reply.get("in_reply_to_id")) != str(post_id):
                continue
            author = reply["account"]
            comments.append(
                Comment(
                    platform=self.platform_name,
                    comment_id=reply["id"],
                    root_id=str(post_id),
                    author_id=author["id"],
                    author=author["acct"],
                    text=html.unescape(re.sub(r"<[^>]*>", " ", reply["content"])).strip(),
                    created_at=reply["created_at"],
                    url=reply.get("url") or "",
                    is_own=author["id"] == own_id,
                    is_bot=author.get("bot", False),
                    answered=any(
                        child.get("in_reply_to_id") == reply["id"] and child.get("account", {}).get("id") == own_id
                        for child in descendants
                    ),
                    context={"visibility": reply["visibility"]},
                )
            )
        return comments

    def reply(self, comment: Comment, text: str) -> PostResult:
        token = (os.environ.get("MASTODON_TOKEN") or "").strip()
        if not token:
            return PostResult(success=False, error_message="Mastodon token missing")
        response = requests.post(
            f"{self.base}/api/v1/statuses",
            headers={"Authorization": f"Bearer {token}", "Idempotency-Key": comment.key},
            data={
                "status": f"@{comment.author} {text}",
                "in_reply_to_id": comment.comment_id,
                "visibility": comment.context.get("visibility", "unlisted"),
            },
            timeout=25,
        )
        response.raise_for_status()
        return PostResult(success=True, post_id=response.json()["id"], post_url=response.json().get("url"))


class InstagramReplies:
    platform_name = "Instagram"

    def __init__(self) -> None:
        self.account_id = os.environ.get("INSTAGRAM_BUSINESS_ACCOUNT_ID")
        self.token = os.environ.get("INSTAGRAM_PAGE_ACCESS_TOKEN")

    def read(self, post: PublishedPost) -> list[Comment]:
        if not self.token or not self.account_id:
            raise ValueError("Instagram account ID or token missing")
        headers = {"Authorization": f"Bearer {self.token}"}
        params = {"fields": "id,text,timestamp,from,hidden,replies{id,from}", "limit": "100"}
        comments = []
        for _ in range(5):
            page = get_json(f"{GRAPH_API_BASE}/{post['post_id']}/comments", headers=headers, params=params)
            for reply in page.get("data", []):
                if reply.get("hidden"):
                    continue
                author = reply.get("from", {})
                comments.append(
                    Comment(
                        platform=self.platform_name,
                        comment_id=reply["id"],
                        root_id=str(post["post_id"]),
                        author_id=author.get("id", ""),
                        author=author.get("username", ""),
                        text=reply.get("text", ""),
                        created_at=reply["timestamp"],
                        is_own=author.get("id") == self.account_id,
                        answered=any(
                            child.get("from", {}).get("id") == self.account_id
                            for child in reply.get("replies", {}).get("data", [])
                        ),
                    )
                )
            paging = page.get("paging", {})
            after = paging.get("cursors", {}).get("after")
            if not paging.get("next") or not after:
                break
            params["after"] = after
        return comments

    def reply(self, comment: Comment, text: str) -> PostResult:
        if not self.token:
            return PostResult(success=False, error_message="Instagram token missing")
        response = requests.post(
            f"{GRAPH_API_BASE}/{comment.comment_id}/replies",
            headers={"Authorization": f"Bearer {self.token}"},
            data={"message": text},
            timeout=25,
        )
        response.raise_for_status()
        return PostResult(success=True, post_id=response.json()["id"])
