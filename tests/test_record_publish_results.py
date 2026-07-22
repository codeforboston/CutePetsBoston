import json
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from abstractions import AdoptablePet, PostResult
from main import pick_pet, record_publish_results


def make_pet(pet_id="pet-123", name="Poppy"):
    return AdoptablePet(
        name=name,
        species="dog",
        breed="mutt",
        location="Boston, MA",
        image_url="https://example.com/poppy.jpg",
        adoption_url="https://example.com/adopt/poppy",
        pet_id=pet_id,
    )


def test_pick_pet_preserves_dedup_without_writing(tmp_path):
    database_path = tmp_path / "database.json"
    database_path.write_text(
        json.dumps(
            {
                "posted_pets": [
                    {
                        "name": "Already posted",
                        "pet_id": "old-pet",
                        "posted_at": datetime.now(timezone.utc).isoformat(),
                    }
                ]
            }
        )
    )
    original_contents = database_path.read_text()

    selected = pick_pet(
        [make_pet("old-pet", "Old"), make_pet("new-pet", "New")],
        database_path=database_path,
    )

    assert selected.pet_id == "new-pet"
    assert database_path.read_text() == original_contents


def test_pick_pet_does_not_create_a_missing_database(tmp_path):
    database_path = tmp_path / "database.json"

    selected = pick_pet([make_pet()], database_path=database_path)

    assert selected.pet_id == "pet-123"
    assert not database_path.exists()


def test_records_pet_and_one_post_per_successful_publish(tmp_path):
    database_path = tmp_path / "database.json"
    pet = make_pet()
    bluesky = SimpleNamespace(platform_name="Bluesky")
    mastodon = SimpleNamespace(platform_name="Mastodon")

    record_publish_results(
        pet,
        [
            (
                bluesky,
                PostResult(
                    success=True,
                    post_id="cid-123",
                    post_url="at://did:plc:abc/app.bsky.feed.post/xyz",
                ),
            ),
            (
                mastodon,
                PostResult(success=False, error_message="publish failed"),
            ),
        ],
        database_path=database_path,
    )

    data = json.loads(database_path.read_text())
    assert data["posted_pets"][0]["pet_id"] == "pet-123"
    assert data["posts"] == [
        {
            "pet_id": "pet-123",
            "platform": "Bluesky",
            "post_id": "cid-123",
            "post_url": "at://did:plc:abc/app.bsky.feed.post/xyz",
            "posted_at": data["posted_pets"][0]["posted_at"],
            "metrics": [],
        }
    ]
    assert not database_path.with_name("database.json.tmp").exists()


def test_records_pet_when_all_publishes_fail(tmp_path):
    database_path = tmp_path / "database.json"
    poster = SimpleNamespace(platform_name="Mastodon")

    record_publish_results(
        make_pet(),
        [(poster, PostResult(success=False, error_message="publish failed"))],
        database_path=database_path,
    )

    data = json.loads(database_path.read_text())
    assert [pet["pet_id"] for pet in data["posted_pets"]] == ["pet-123"]
    assert data["posts"] == []


def test_prunes_old_pets_and_posts_independently(tmp_path):
    database_path = tmp_path / "database.json"
    old_timestamp = (datetime.now(timezone.utc) - timedelta(weeks=13)).isoformat()
    database_path.write_text(
        json.dumps(
            {
                "posted_pets": [
                    {"name": "Old pet", "pet_id": "old-pet", "posted_at": old_timestamp}
                ],
                "posts": [
                    {
                        "pet_id": "different-old-pet",
                        "platform": "Bluesky",
                        "post_id": "old-post",
                        "post_url": "at://old",
                        "posted_at": old_timestamp,
                        "metrics": [],
                    }
                ],
            }
        )
    )

    record_publish_results(make_pet(), [], database_path=database_path)

    data = json.loads(database_path.read_text())
    assert [pet["pet_id"] for pet in data["posted_pets"]] == ["pet-123"]
    assert data["posts"] == []
