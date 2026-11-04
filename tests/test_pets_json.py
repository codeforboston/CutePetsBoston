import json
from datetime import datetime, timedelta, timezone

from abstractions import AdoptablePet
from database import PublishedPost
from pets_json import BLURB_MAX_CHARS, build_pet_cards, write_pets_json


def make_pet(
    pet_id="pet-123",
    name="ChaCha",
    species="dog",
    breed="Terrier mix",
    description="A calm, obedient terrier mix who is house trained.",
    image_urls=("https://example.com/chacha.jpg",),
    age_string=None,
    sex=None,
):
    return AdoptablePet(
        name=name,
        species=species,
        breed=breed,
        location="Boston, MA",
        description=description,
        image_urls=list(image_urls),
        age_string=age_string,
        sex=sex,
        pet_id=pet_id,
    )


def make_post(
    pet_id="pet-123",
    platform="Mastodon",
    post_url: str | None = "https://mastodon.social/@cutepetsboston/1",
    posted_at=None,
) -> PublishedPost:
    """A post record shaped like what main.py writes to database.json."""
    posted_at = posted_at or datetime.now(timezone.utc)
    return {
        "pet_id": pet_id,
        "platform": platform,
        "post_id": "debug",
        "post_url": post_url,
        "posted_at": posted_at.isoformat(),
        "metrics": [],
    }


def test_joins_posts_to_fetched_pets_newest_first():
    today = datetime.now(timezone.utc)
    yesterday = today - timedelta(days=1)
    two_days_ago = today - timedelta(days=2)

    cards = build_pet_cards(
        [make_pet("pet-a", "Aster"), make_pet("pet-b", "Bowie", species="cat")],
        [
            make_post("pet-a", posted_at=yesterday),
            make_post("pet-b", posted_at=two_days_ago),
            make_post("pet-a", posted_at=today),
        ],
    )

    assert [card["name"] for card in cards] == ["Aster", "Bowie"]
    assert [card["posted_date"] for card in cards] == [today.date().isoformat(), two_days_ago.date().isoformat()]


def test_dedupes_per_pet_preferring_the_mastodon_post_url():
    bluesky_time = datetime.now(timezone.utc)
    mastodon_time = bluesky_time - timedelta(hours=1)  # the Mastodon record is older

    cards = build_pet_cards(
        [make_pet()],
        [
            make_post(platform="Bluesky", post_url="at://did:plc:abc/app.bsky.feed.post/xyz", posted_at=bluesky_time),
            make_post(
                platform="Mastodon", post_url="https://mastodon.social/@cutepetsboston/117", posted_at=mastodon_time
            ),
        ],
    )

    assert len(cards) == 1
    assert cards[0]["post_url"] == "https://mastodon.social/@cutepetsboston/117"


def test_falls_back_to_any_platform_without_a_mastodon_post():
    cards = build_pet_cards(
        [make_pet()],
        [make_post(platform="Instagram", post_url="https://www.instagram.com/cutepetsboston/")],
    )

    assert cards[0]["post_url"] == "https://www.instagram.com/cutepetsboston/"


def test_drops_posts_whose_pet_left_the_pool():
    cards = build_pet_cards(
        [make_pet("pet-a")],
        [make_post("pet-a"), make_post("pet-adopted", post_url="https://mastodon.social/@cutepetsboston/99")],
    )

    assert [card["name"] for card in cards] == ["ChaCha"]


def test_caps_the_feed_at_eight_cards():
    pets = [make_pet(f"pet-{i}", name=f"Pet {i}") for i in range(10)]
    posts = [
        make_post(
            f"pet-{i}",
            post_url=f"https://mastodon.social/@cutepetsboston/{i}",
            posted_at=datetime.now(timezone.utc) - timedelta(hours=i),
        )
        for i in range(10)
    ]

    cards = build_pet_cards(pets, posts)

    assert len(cards) == 8
    assert [card["name"] for card in cards] == [f"Pet {i}" for i in range(8)]  # the newest pets win


def test_nothing_joins_builds_an_empty_feed():
    cards = build_pet_cards([make_pet()], [make_post("pet-elsewhere")])

    assert cards == []


def test_summarizes_the_description_as_a_first_sentence():
    cards = build_pet_cards([make_pet(description="A calm, obedient girl. House trained. Loves naps.")], [make_post()])

    assert cards[0]["blurb"] == "A calm, obedient girl."


def test_truncates_a_description_with_no_sentence():
    long_description = " ".join(["word"] * 60)
    cards = build_pet_cards([make_pet(description=long_description)], [make_post()])

    blurb = cards[0]["blurb"]
    assert len(blurb) <= BLURB_MAX_CHARS
    assert blurb.endswith("\u2026")


def test_carries_photo_and_structural_fields_for_the_frontend():
    cards = build_pet_cards(
        [make_pet(species="cat", age_string="Kitten", sex="Male", image_urls=[])],
        [make_post()],
    )

    cat_card = cards[0]
    assert cat_card["species"] == "cat"
    assert cat_card["image_url"] is None  # feeds the illustration fallback
    assert cat_card["age"] == "Kitten"
    assert cat_card["sex"] == "Male"
    assert cat_card["location"] == "Boston, MA"


def test_reports_a_joined_pet_that_has_no_link_anywhere():
    warnings = []

    build_pet_cards([make_pet()], [make_post(post_url=None)], warning_callback=warnings.append)

    assert len(warnings) == 1
    assert "ChaCha" in warnings[0]


def test_does_not_alert_when_a_post_cannot_join_the_pool():
    # Ordinary attrition (adopted pets, debug records) just leaves the feed.
    warnings = []
    build_pet_cards(
        [make_pet()],
        [make_post("pet-unknown"), make_post("pet-elsewhere", post_url=None)],
        warning_callback=warnings.append,
    )

    assert warnings == []


def test_write_pets_json_saves_atomically_from_the_database(tmp_path):
    database_path = tmp_path / "database.json"
    database_path.write_text(json.dumps({"posts": [make_post()]}))
    pets_path = tmp_path / "pets.json"

    write_pets_json([make_pet()], database_path=database_path, pets_path=pets_path)

    cards = json.loads(pets_path.read_text())
    assert [card["name"] for card in cards] == ["ChaCha"]
    assert not pets_path.with_name("pets.json.tmp").exists()


def test_write_pets_json_creates_an_empty_file_when_nothing_joins(tmp_path):
    database_path = tmp_path / "database.json"
    database_path.write_text(json.dumps({"posts": [make_post("pet-elsewhere")]}))
    pets_path = tmp_path / "pets.json"

    write_pets_json([make_pet()], database_path=database_path, pets_path=pets_path)

    assert json.loads(pets_path.read_text()) == []
