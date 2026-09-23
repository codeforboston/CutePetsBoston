from unittest.mock import Mock, patch

from abstractions import AdoptablePet, Post
from adoption_sources.rescue_groups import SourceRescueGroups
from social_posters.bluesky import PosterBluesky
from social_posters.instagram import PosterInstagram
from social_posters.mastodon import PosterMastodon


URLS = [f"https://example.com/{number}.jpg" for number in range(1, 6)]


def make_post(count=4):
    return Post(text="Meet Buddy", image_urls=URLS[:count], alt_text="Photo of Buddy")


def make_response(data=None, content=b"photo"):
    response = Mock()
    response.json.return_value = data or {}
    response.content = content
    response.headers = {"Content-Type": "image/jpeg"}
    return response


def test_rescuegroups_uses_ordered_distinct_large_pictures_and_caps_at_four():
    source = SourceRescueGroups(api_key="dummy")
    animal = {
        "id": "123",
        "attributes": {"name": "Buddy", "pictureThumbnailUrl": "https://example.com/thumb.jpg?width=100"},
        "relationships": {
            "species": {"data": [{"id": "dog"}]},
            "pictures": {"data": [{"id": str(n)} for n in range(1, 7)]},
        },
    }
    pictures = {
        "1": {"order": 3, "large": URLS[2]},
        "2": {"order": 1, "large": URLS[0]},
        "3": {"order": 2, "large": URLS[1]},
        "4": {"order": 4, "large": URLS[2]},
        "5": {"order": 5, "large": URLS[3]},
        "6": {"order": 6, "large": URLS[4]},
    }
    pet = source._parse_animal(animal, {}, {"dog": {"plural": "dogs"}}, pictures)
    assert pet.image_urls == URLS[:4]

    fallback = source._parse_animal(animal, {}, {"dog": {"plural": "dogs"}}, {})
    assert fallback.image_urls == ["https://example.com/thumb.jpg?width=800"]


def test_rescuegroups_requests_and_joins_picture_includes():
    source = SourceRescueGroups(api_key="dummy")
    animal = {
        "id": "123",
        "attributes": {"name": "Buddy", "pictureThumbnailUrl": URLS[0]},
        "relationships": {
            "species": {"data": [{"id": "dog"}]},
            "pictures": {"data": [{"id": "picture-1"}]},
        },
    }
    response = make_response({
        "data": [animal],
        "included": [
            {"type": "species", "id": "dog", "attributes": {"plural": "dogs"}},
            {"type": "pictures", "id": "picture-1", "attributes": {"order": 1, "large": URLS[1]}},
        ],
    })
    session = Mock()
    session.post.return_value = response
    with patch("adoption_sources.rescue_groups._session_with_retries", return_value=session):
        pets = list(source.fetch_pets())
    assert "include=orgs,breeds,locations,species,pictures" in session.post.call_args.args[0]
    assert pets[0].image_urls == [URLS[1]]


def test_pet_and_post_use_ordered_image_urls_only():
    selected_post = Post(text="gallery", image_urls=[*URLS, URLS[0]])
    assert selected_post.selected_image_urls == URLS[:4]
    assert selected_post.selected_image_urls is selected_post.selected_image_urls
    assert selected_post.image_urls == [*URLS, URLS[0]]
    assert "image_url" not in AdoptablePet.__dataclass_fields__
    assert "image_url" not in Post.__dataclass_fields__
    pet = AdoptablePet("Buddy", "dog", "Mix", "Boston", image_urls=URLS[:2])
    assert pet.image_urls == URLS[:2]
    assert AdoptablePet("Buddy", "dog", "Mix", "Boston", image_urls=[*URLS, URLS[0]]).image_urls == URLS[:4]
    post = PosterInstagram().format_post(pet)
    assert post.image_urls == URLS[:2]


def test_bluesky_embeds_four_photos_and_skips_one_failed_upload():
    poster = PosterBluesky.__new__(PosterBluesky)
    poster._is_available = True
    poster._access_token = "token"
    poster._did = "did:test"
    records = []
    fail_second = False

    def send(url, **kwargs):
        if url.endswith("uploadBlob"):
            if fail_second and kwargs["data"] == b"photo-2":
                raise RuntimeError("upload failed")
            return make_response({"blob": kwargs["data"].decode()})
        records.append(kwargs["json"]["record"])
        return make_response({"cid": "cid", "uri": "at://post"})

    def download(url, **_kwargs):
        return make_response(content=f"photo-{URLS.index(url) + 1}".encode())

    with patch("social_posters.bluesky.requests.get", side_effect=download), patch(
        "social_posters.bluesky.requests.post", side_effect=send
    ):
        assert poster.publish(make_post()).success
        assert len(records[-1]["embed"]["images"]) == 4
        fail_second = True
        assert poster.publish(make_post()).success
        assert len(records[-1]["embed"]["images"]) == 3
        assert poster.publish(make_post(1)).success
        assert len(records[-1]["embed"]["images"]) == 1


def test_bluesky_does_not_publish_without_a_usable_photo():
    poster = PosterBluesky.__new__(PosterBluesky)
    poster._is_available = True
    poster._access_token = "token"
    poster._did = "did:test"
    with patch("social_posters.bluesky.requests.get", side_effect=RuntimeError("download failed")), patch(
        "social_posters.bluesky.requests.post"
    ) as send:
        assert not poster.publish(make_post(1)).success
    send.assert_not_called()


def test_mastodon_attaches_remaining_photos_to_root_status():
    poster = PosterMastodon.__new__(PosterMastodon)
    poster._is_available = True
    session = Mock()
    poster._session = session
    session.media_post.side_effect = [
        {"id": "1"}, RuntimeError("bad image"), {"id": "3"}, {"id": "4"}
    ]
    session.status_post.return_value = {"id": "posted", "url": "https://example.com/post"}
    with patch.object(poster, "_download_image", side_effect=[f"/missing/{n}" for n in range(4)]):
        assert poster.publish(make_post()).success
    assert poster._session is None
    assert session.status_post.call_args_list[0].kwargs["media_ids"] == ["1", "3", "4"]


def test_mastodon_attaches_four_photos_when_all_work():
    poster = PosterMastodon.__new__(PosterMastodon)
    poster._is_available = True
    session = Mock()
    session.media_post.side_effect = [{"id": str(index)} for index in range(1, 5)]
    session.status_post.return_value = {"id": "posted"}
    poster._session = session
    with patch.object(poster, "_download_image", side_effect=[f"/missing/{n}" for n in range(4)]):
        assert poster.publish(make_post()).success
    assert session.status_post.call_args_list[0].kwargs["media_ids"] == ["1", "2", "3", "4"]


def test_mastodon_single_photo_and_no_usable_photo():
    poster = PosterMastodon.__new__(PosterMastodon)
    poster._is_available = True
    session = Mock()
    session.media_post.return_value = {"id": "one"}
    session.status_post.return_value = {"id": "posted"}
    poster._session = session
    with patch.object(poster, "_download_image", return_value="/missing/photo"):
        assert poster.publish(make_post(1)).success
    assert session.status_post.call_args_list[0].kwargs["media_ids"] == ["one"]

    poster._session = session
    session.media_post.side_effect = RuntimeError("bad")
    with patch.object(poster, "_download_image", return_value="/missing/photo"):
        assert not poster.publish(make_post(1)).success


def test_instagram_uses_carousel_for_four_and_single_container_for_one():
    poster = PosterInstagram.__new__(PosterInstagram)
    poster._is_available = True
    poster._authenticated = True
    poster.account_id = "account"
    poster.access_token = "token"
    poster.username = None
    calls = []

    def send(url, **kwargs):
        data = kwargs["data"]
        calls.append(data)
        return make_response({"id": f"container-{len(calls)}"})

    with patch("social_posters.instagram.requests.post", side_effect=send), patch(
        "social_posters.instagram.requests.get", return_value=make_response({"status_code": "FINISHED"})
    ):
        assert poster.publish(make_post()).success
        assert [call.get("is_carousel_item") for call in calls[:4]] == ["true"] * 4
        assert [call["alt_text"] for call in calls[:4]] == [f"Photo of Buddy (photo {n})" for n in range(1, 5)]
        assert calls[4]["media_type"] == "CAROUSEL"
        assert calls[4]["children"] == "container-1,container-2,container-3,container-4"
        calls.clear()
        assert poster.publish(make_post(1)).success
        assert calls[0]["image_url"] == URLS[0]
        assert calls[0]["alt_text"] == "Photo of Buddy (photo 1)"
        assert "media_type" not in calls[0]


def test_instagram_skips_failed_children_and_falls_back_to_single():
    poster = PosterInstagram.__new__(PosterInstagram)
    poster._is_available = True
    poster._authenticated = True
    poster.account_id = "account"
    poster.access_token = "token"
    poster.username = None
    calls = []

    def send(url, **kwargs):
        data = kwargs["data"]
        calls.append(data)
        if data.get("is_carousel_item") and data["image_url"] != URLS[2]:
            raise RuntimeError("unusable")
        return make_response({"id": f"container-{len(calls)}"})

    with patch("social_posters.instagram.requests.post", side_effect=send), patch(
        "social_posters.instagram.requests.get", return_value=make_response({"status_code": "FINISHED"})
    ):
        assert poster.publish(make_post()).success
    assert calls[-2]["image_url"] == URLS[2]
    assert calls[-2]["alt_text"] == "Photo of Buddy (photo 3)"
    assert "is_carousel_item" not in calls[-2]
    assert "media_type" not in calls[-2]


def test_instagram_does_not_publish_without_a_usable_photo():
    poster = PosterInstagram.__new__(PosterInstagram)
    poster._is_available = True
    poster._authenticated = True
    poster.account_id = "account"
    poster.access_token = "token"
    poster.username = None
    with patch("social_posters.instagram.requests.post", side_effect=RuntimeError("bad image")) as send:
        assert not poster.publish(make_post(2)).success
    assert send.call_count == 2
