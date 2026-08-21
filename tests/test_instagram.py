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
