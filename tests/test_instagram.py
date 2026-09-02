from unittest.mock import Mock, patch

from abstractions import Post
from social_posters.instagram import GRAPH_API_BASE, PosterInstagram


ACCESS_TOKEN = "secret-token"
ACCOUNT_ID = "account-id"


def build_poster(monkeypatch) -> PosterInstagram:
    monkeypatch.setenv("INSTAGRAM_BUSINESS_ACCOUNT_ID", ACCOUNT_ID)
    monkeypatch.setenv("INSTAGRAM_PAGE_ACCESS_TOKEN", ACCESS_TOKEN)
    return PosterInstagram()


def test_authenticate_keeps_access_token_out_of_query_params(monkeypatch):
    poster = build_poster(monkeypatch)
    response = Mock()
    response.json.return_value = {"id": ACCOUNT_ID, "username": "cutepetsboston2026_test"}

    with patch(
        "social_posters.instagram.requests.get",
        return_value=response,
    ) as request_get:
        assert poster.authenticate() is True

    request_get.assert_called_once_with(
        f"{GRAPH_API_BASE}/{ACCOUNT_ID}",
        params={"fields": "id,username"},
        headers={"Authorization": f"Bearer {ACCESS_TOKEN}"},
        timeout=10,
    )
    response.raise_for_status.assert_called_once_with()
    assert poster.username == "cutepetsboston2026_test"


def test_create_media_container_uses_authorization_header(monkeypatch):
    poster = build_poster(monkeypatch)
    response = Mock()
    response.json.return_value = {"id": "container-id"}
    post = Post(text="Meet Poppy!", image_url="https://example.com/poppy.jpg")

    with patch(
        "social_posters.instagram.requests.post",
        return_value=response,
    ) as request_post:
        container_id = poster._create_media_container(post)

    assert container_id == "container-id"
    request_post.assert_called_once_with(
        f"{GRAPH_API_BASE}/{ACCOUNT_ID}/media",
        headers={"Authorization": f"Bearer {ACCESS_TOKEN}"},
        data={
            "image_url": "https://example.com/poppy.jpg",
            "caption": "Meet Poppy!",
        },
        timeout=30,
    )
    response.raise_for_status.assert_called_once_with()


def test_publish_media_uses_authorization_header(monkeypatch):
    poster = build_poster(monkeypatch)
    response = Mock()
    response.json.return_value = {"id": "media-id"}

    with patch(
        "social_posters.instagram.requests.post",
        return_value=response,
    ) as request_post:
        media_id = poster._publish_media("container-id")

    assert media_id == "media-id"
    request_post.assert_called_once_with(
        f"{GRAPH_API_BASE}/{ACCOUNT_ID}/media_publish",
        headers={"Authorization": f"Bearer {ACCESS_TOKEN}"},
        data={"creation_id": "container-id"},
        timeout=30,
    )
    response.raise_for_status.assert_called_once_with()


def test_wait_for_container_ready_returns_once_finished(monkeypatch):
    poster = build_poster(monkeypatch)
    in_progress = Mock()
    in_progress.json.return_value = {"status_code": "IN_PROGRESS"}
    finished = Mock()
    finished.json.return_value = {"status_code": "FINISHED"}

    with (
        patch(
            "social_posters.instagram.requests.get",
            side_effect=[in_progress, finished],
        ) as request_get,
        patch("social_posters.instagram.time.sleep") as mock_sleep,
    ):
        poster._wait_for_container_ready("container-id")

    assert request_get.call_count == 2
    request_get.assert_called_with(
        f"{GRAPH_API_BASE}/container-id",
        params={"fields": "status_code"},
        headers={"Authorization": f"Bearer {ACCESS_TOKEN}"},
        timeout=10,
    )
    mock_sleep.assert_called_once()


def test_wait_for_container_ready_raises_on_error_status(monkeypatch):
    poster = build_poster(monkeypatch)
    response = Mock()
    response.json.return_value = {"status_code": "ERROR"}

    with patch("social_posters.instagram.requests.get", return_value=response):
        try:
            poster._wait_for_container_ready("container-id")
            assert False, "expected RuntimeError"
        except RuntimeError as exc:
            assert "ERROR" in str(exc)


def test_publish_builds_post_url_from_authenticated_username(monkeypatch):
    poster = build_poster(monkeypatch)
    poster._authenticated = True
    poster.username = "cutepetsboston2026_test"
    post = Post(text="Meet Poppy!", image_url="https://example.com/poppy.jpg")

    with (
        patch.object(poster, "_create_media_container", return_value="container-id"),
        patch.object(poster, "_wait_for_container_ready"),
        patch.object(poster, "_publish_media", return_value="media-id"),
    ):
        result = poster.publish(post)

    assert result.success is True
    assert result.post_id == "media-id"
    assert result.post_url == "https://www.instagram.com/cutepetsboston2026_test/"
