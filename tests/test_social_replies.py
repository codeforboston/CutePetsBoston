import json
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch

import pytest
import requests

from abstractions import PostResult
from database import PublishedPost
from reply_inbox import audit, main, send_proposals, sending_lock
from social_replies.adapters import BlueskyReplies, InstagramReplies, MastodonReplies
from social_replies.engine import ReplyPolicy, pick_replies
from social_replies.models import Comment

NOW = datetime(2026, 11, 3, 18, tzinfo=timezone.utc)


def comment(number=1, **changes):
    values: dict = dict(
        platform="Bluesky",
        comment_id=str(number),
        root_id=f"root-{number}",
        author_id="human",
        author="human.example",
        text="So cute! 🐾",
        created_at=NOW.isoformat(),
    )
    values.update(changes)
    return Comment(**values)


def saved_post(platform: str, post_id: str = "root", post_url: str = "") -> PublishedPost:
    return {
        "pet_id": "pet",
        "platform": platform,
        "post_id": post_id,
        "post_url": post_url,
        "posted_at": NOW.isoformat(),
    }


def test_sampling_is_stable_and_roughly_one_in_three():
    comments = [comment(number) for number in range(1000)]
    policy = ReplyPolicy(daily_cap=1000)
    first = pick_replies(comments, policy, now=NOW)
    assert first == pick_replies(list(reversed(comments)), policy, now=NOW)
    assert 280 < len(first) < 390


@pytest.mark.parametrize(
    "changes",
    [
        {"is_own": True},
        {"is_bot": True},
        {"answered": True},
        {"author_id": ""},
        {"text": "How can I apply?"},
        {"text": "Sorry for your loss"},
        {"text": "https://spam.example"},
        {"text": ""},
        {"text": "x" * 121},
        {"created_at": "invalid"},
        {"created_at": (NOW - timedelta(days=8)).isoformat()},
        {"created_at": (NOW + timedelta(days=1)).isoformat()},
    ],
)
def test_ineligible_comments_do_not_get_silly_replies(changes):
    assert pick_replies([comment(**changes)], ReplyPolicy(rate=1), now=NOW) == []


def test_history_daily_cap_and_threads_apply_across_platforms():
    comments = [comment(1), comment(2, root_id="root-1"), comment(3, platform="Instagram"), comment(4)]
    selected = pick_replies(comments, ReplyPolicy(rate=1, daily_cap=3), history={"old": NOW.isoformat()}, now=NOW)
    assert len(selected) == 2
    assert len({item.thread_key for item, _ in selected}) == 2
    assert pick_replies([comment()], ReplyPolicy(rate=1), history={comment().key: NOW.isoformat()}, now=NOW) == []
    assert pick_replies([comment()], ReplyPolicy(rate=1), now=NOW, blocked_threads={"Bluesky:root-1"}) == []


def test_pool_contains_requested_phrase_and_cross_species_sounds():
    from social_replies.engine import POOL_PATH

    pool = json.loads(POOL_PATH.read_text())
    assert "Who let the dogs out? Woof woof! 🐶" in pool
    assert "Meow meow! 😸" in pool
    assert "Woof woof! 🐶" in pool


def test_send_reserves_before_network_and_does_not_retry_uncertain_result(tmp_path):
    path = tmp_path / "state.json"
    adapter = Mock(platform_name="Bluesky")
    state = {"processed": {}}
    incoming = comment()

    def failed_send(*args):
        saved = json.loads(path.read_text())
        assert saved["processed"][incoming.key]["status"] == "pending"
        raise requests.Timeout()

    adapter.reply.side_effect = failed_send
    proposals = [(incoming, "Meow meow! 😸")]
    assert send_proposals(proposals, [adapter], state, path) == [{"comment": incoming.key, "success": False}]
    assert state["processed"][incoming.key]["status"] == "needs_review"
    assert send_proposals(proposals, [adapter], state, path) == []
    assert adapter.reply.call_count == 1


def test_preview_never_sends_or_creates_sending_state(tmp_path, monkeypatch):
    output = tmp_path / "inbox.json"
    state = tmp_path / "state.json"
    monkeypatch.setattr("sys.argv", ["reply_inbox.py", "--output", str(output), "--state", str(state), "--rate", "1"])
    incoming = comment(created_at=datetime.now(timezone.utc).isoformat())
    with patch("reply_inbox.audit", return_value=([incoming], {})), patch("requests.post") as post:
        main()
    post.assert_not_called()
    assert json.loads(output.read_text())["mode"] == "preview"
    assert not state.exists()


def test_audit_reports_access_errors_instead_of_claiming_an_empty_inbox(tmp_path):
    database = tmp_path / "database.json"
    database.write_text(
        json.dumps(
            {"posts": [{"platform": "Instagram", "post_id": "1", "posted_at": datetime.now(timezone.utc).isoformat()}]}
        )
    )
    adapter = Mock(platform_name="Instagram")
    response = requests.Response()
    response.status_code = 403
    adapter.read.side_effect = requests.HTTPError(response=response)
    comments, coverage = audit(database, [adapter])
    assert comments == []
    assert coverage["Instagram"]["checked_posts"] == 0
    assert coverage["Instagram"]["errors"][0]["http_status"] == 403
    assert coverage["Instagram"]["stopped_early"]
    assert coverage["Instagram"]["external_comments"] is None


def test_concurrent_senders_cannot_share_state_until_first_finishes(tmp_path):
    path = tmp_path / "state.json"
    with sending_lock(path):
        with pytest.raises(FileExistsError):
            with sending_lock(path):
                pytest.fail("Second sender acquired the first sender's lock")
    with sending_lock(path):
        assert path.with_name("state.json.lock").exists()
    assert not path.with_name("state.json.lock").exists()


def test_bluesky_preserves_reply_references_and_detects_our_response():
    uri = "at://did:plc:own/app.bsky.feed.post/root"
    node = {
        "post": {
            "uri": "at://did:plc:human/app.bsky.feed.post/comment",
            "cid": "child-cid",
            "author": {"did": "did:plc:human", "handle": "human.example"},
            "record": {"text": "Cute!", "createdAt": NOW.isoformat(), "reply": {"parent": {"uri": uri}}},
        },
        "replies": [{"post": {"author": {"did": "did:plc:own"}}}],
    }
    tree = {"thread": {"post": {"cid": "root-cid", "author": {"did": "did:plc:own"}}, "replies": [node]}}
    with patch("social_replies.adapters.get_json", return_value=tree):
        result = BlueskyReplies().read(saved_post("Bluesky", post_url=uri))
    assert result[0].answered
    assert result[0].context == {"root_cid": "root-cid", "parent_cid": "child-cid"}


def test_mastodon_only_reads_direct_comments_and_strips_markup():
    parent = {
        "id": "comment",
        "in_reply_to_id": "root",
        "account": {"id": "human", "acct": "human"},
        "content": "<p>Aww &amp; cute!</p>",
        "created_at": NOW.isoformat(),
        "visibility": "public",
    }
    child = dict(parent, id="child", in_reply_to_id="comment")
    with patch(
        "social_replies.adapters.get_json", side_effect=[{"account": {"id": "own"}}, {"descendants": [parent, child]}]
    ):
        result = MastodonReplies().read(saved_post("Mastodon"))
    assert len(result) == 1
    assert result[0].text == "Aww & cute!"


def test_instagram_pagination_keeps_token_on_our_endpoint(monkeypatch):
    monkeypatch.setenv("INSTAGRAM_PAGE_ACCESS_TOKEN", "test-token")
    monkeypatch.setenv("INSTAGRAM_BUSINESS_ACCOUNT_ID", "own")
    incoming = {
        "id": "comment",
        "text": "Cute!",
        "timestamp": NOW.isoformat(),
        "from": {"id": "human"},
        "replies": {"data": [{"from": {"id": "own"}}]},
    }
    pages = [
        {"data": [incoming], "paging": {"next": "https://untrusted.example", "cursors": {"after": "cursor"}}},
        {"data": []},
    ]
    with patch("social_replies.adapters.get_json", side_effect=pages) as get:
        result = InstagramReplies().read(saved_post("Instagram", post_id="media"))
    assert result[0].answered
    assert get.call_args_list[0].args[0] == get.call_args_list[1].args[0]
    assert get.call_args_list[1].kwargs["params"]["after"] == "cursor"


def test_successful_send_is_saved(tmp_path):
    adapter = Mock(platform_name="Bluesky")
    adapter.reply.return_value = PostResult(success=True, post_id="sent-id")
    state = {"processed": {}}
    send_proposals([(comment(), "Woof!")], [adapter], state, tmp_path / "state.json")
    assert state["processed"][comment().key]["status"] == "sent"


def test_bluesky_send_uses_both_thread_and_parent_references():
    incoming = comment(context={"root_cid": "root-hash", "parent_cid": "comment-hash"})
    with patch("social_replies.adapters.PosterBluesky") as poster, patch("requests.post") as post:
        poster.return_value.authenticate.return_value = True
        poster.return_value._access_token = "test-token"
        poster.return_value._did = "did:plc:own"
        post.return_value.json.return_value = {"uri": "at://sent"}
        result = BlueskyReplies().reply(incoming, "Meow meow! 😸")
    assert result.success
    record = post.call_args.kwargs["json"]["record"]
    assert record["reply"] == {
        "root": {"uri": incoming.root_id, "cid": "root-hash"},
        "parent": {"uri": incoming.comment_id, "cid": "comment-hash"},
    }


def test_instagram_send_targets_comment_replies_not_media(monkeypatch):
    monkeypatch.setenv("INSTAGRAM_PAGE_ACCESS_TOKEN", "test-token")
    with patch("requests.post") as post:
        post.return_value.json.return_value = {"id": "sent"}
        result = InstagramReplies().reply(comment(comment_id="incoming"), "Woof! 🐶")
    assert result.success
    assert post.call_args.args[0].endswith("/incoming/replies")
    assert post.call_args.kwargs["data"] == {"message": "Woof! 🐶"}


def test_mastodon_send_mentions_author_and_preserves_visibility(monkeypatch):
    monkeypatch.setenv("MASTODON_TOKEN", "test-token")
    incoming = comment(context={"visibility": "unlisted"})
    with patch("requests.post") as post:
        post.return_value.json.return_value = {"id": "sent"}
        result = MastodonReplies().reply(incoming, "Blep. 😛")
    assert result.success
    args = post.call_args.kwargs
    assert args["data"] == {
        "status": "@human.example Blep. 😛",
        "in_reply_to_id": incoming.comment_id,
        "visibility": "unlisted",
    }
    assert args["headers"]["Idempotency-Key"] == incoming.key
