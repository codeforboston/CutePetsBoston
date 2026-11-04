"""Builds ``pets.json``, the pet-card feed behind the homepage.

Every pipeline run joins the post records in database.json to the pets
fetched during this run and writes the newest results to ``pets.json`` at
the repo root, next to ``dashboard.html``. The workflows deploy it with
the same artifact pattern -- see the ``pets_artifact`` wiring in prod.yml
and publish-pages.yml; a web-only push re-deploys the last good copy from
gh-pages.

A pet that has dropped out of the adoption pool (e.g. was adopted) no
longer joins its post record, so its card leaves the feed instead of
advertising a listing that is gone. If nothing joins, an empty file is
written: the homepage then shows its "no recent posts yet" state rather
than a broken deploy.
"""

import json
import logging
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Iterable, TypedDict

from abstractions import AdoptablePet
from database import Database, PublishedPost, read_database

logger = logging.getLogger(__name__)

DEFAULT_PETS_PATH = "pets.json"

# The homepage grid shows the eight freshest cards; anything older is
# ordinary database history, not feed material.
FEED_SIZE = 8

# The platform whose post URL makes the best card link. Bluesky records a
# non-browsable "at://..." URI, so the Mastodon permalink wins when present
# and any other platform with a real URL is the fallback.
PREFERRED_PLATFORM = "Mastodon"

# Card blurbs are the description's first sentence, truncated here when
# even that sentence runs longer than a card.
BLURB_MAX_CHARS = 140

_FIRST_SENTENCE = re.compile(r"^(.+?[.!?])(?:\s|$)")


class PetCard(TypedDict):
    """One card in the homepage feed; pets.json is a JSON array of these."""

    name: str
    species: str
    breed: str
    location: str
    age: str | None
    sex: str | None
    blurb: str
    image_url: str | None
    post_url: str | None
    posted_date: str


def write_pets_json(
    pets: Iterable[AdoptablePet],
    database_path: str | Path = "database.json",
    pets_path: str | Path = DEFAULT_PETS_PATH,
    warning_callback: Callable[[str], None] | None = None,
) -> list[PetCard]:
    """Build this run's feed from ``pets`` and the recorded posts, then save it."""
    data: Database = read_database(database_path)
    cards = build_pet_cards(pets, data.get("posts", []), warning_callback=warning_callback)
    save_pets(cards, pets_path)
    logger.info("Wrote %d pet card(s) to %s", len(cards), pets_path)
    return cards


def build_pet_cards(
    pets: Iterable[AdoptablePet],
    posts: Iterable[PublishedPost],
    warning_callback: Callable[[str], None] | None = None,
) -> list[PetCard]:
    """Join post records to this run's pet pool and build the newest FEED_SIZE cards.

    One card per pet: a pet posted to several platforms still gets a single
    card, linked through Mastodon when it was posted there (see
    choose_post_url). Posts that cannot join the pool are dropped with a log
    entry -- ordinary attrition as pets get adopted. A joined pet with no
    usable link on any platform is unusual enough that it is also surfaced
    to the maintainer via ``warning_callback`` (e.g. a Slack alert).
    """
    pets_by_id = {pet.pet_id: pet for pet in pets if pet.pet_id}

    posts_by_pet: dict[str, list[PublishedPost]] = defaultdict(list)
    for post in posts:
        pet_id = post.get("pet_id")
        pet = pets_by_id.get(pet_id) if isinstance(pet_id, str) else None
        if pet is None:
            logger.warning("Post record for pet_id %r cannot join the fetched pool; dropping it", pet_id)
            continue
        posts_by_pet[pet_id].append(post)

    stamped_cards: list[tuple[datetime, PetCard]] = []
    for pet_id, pet_posts in posts_by_pet.items():
        pet = pets_by_id[pet_id]
        post_url = choose_post_url(pet_posts)
        if post_url is None:
            message = f"Pet {pet.name!r} (pet_id {pet_id!r}) has post records but no usable post_url on any platform"
            logger.warning(message)
            report_warning(message, warning_callback)
            continue
        newest_posted_at = max(posted_datetime(post["posted_at"]) for post in pet_posts)
        stamped_cards.append((newest_posted_at, card_for_pet(pet, post_url, newest_posted_at)))

    stamped_cards.sort(key=lambda card: card[0], reverse=True)
    return [card for _, card in stamped_cards[:FEED_SIZE]]


def card_for_pet(pet: AdoptablePet, post_url: str, posted_at: datetime) -> PetCard:
    """Flatten a joined pet and its winning post into one feed card."""
    return {
        "name": pet.name,
        "species": pet.species,
        "breed": pet.breed,
        "location": pet.location,
        "age": pet.age_string,
        "sex": pet.sex,
        "blurb": summarize_description(pet.description),
        "image_url": pet.image_urls[0] if pet.image_urls else None,
        "post_url": post_url,
        "posted_date": posted_at.date().isoformat(),
    }


def choose_post_url(pet_posts: list[PublishedPost]) -> str | None:
    """Pick the best ``post_url`` among one pet's board posts.

    Mastodon stores a browsable permalink, so its entry wins when present;
    otherwise the first platform that recorded a real URL does.
    """
    for post in pet_posts:
        if post.get("platform") == PREFERRED_PLATFORM and post.get("post_url"):
            return post["post_url"]
    for post in pet_posts:
        if post.get("post_url"):
            return post["post_url"]
    return None


def summarize_description(description: str) -> str:
    """The card blurb: the pet description's first sentence, trimmed to fit."""
    text = " ".join(str(description).split())
    if not text:
        return ""
    matched_sentence = _FIRST_SENTENCE.match(text)
    blurb = matched_sentence.group(1) if matched_sentence else text
    if len(blurb) <= BLURB_MAX_CHARS:
        return blurb
    return text[: BLURB_MAX_CHARS - 1].rstrip() + "\u2026"


def posted_datetime(posted_at: str) -> datetime:
    """Parse a record's ``posted_at`` for ordering.

    Malformed timestamps sort as the oldest possible instant -- the record
    stays joinable, but ordering problems never crash the feed build.
    """
    try:
        return datetime.fromisoformat(posted_at)
    except ValueError, TypeError:
        return datetime.min.replace(tzinfo=timezone.utc)


def report_warning(message: str, warning_callback: Callable[[str], None] | None) -> None:
    """Route an unusual-but-recoverable data problem to the maintainer channel."""
    if warning_callback is None:
        return
    try:
        warning_callback(message)
    except Exception:
        logger.exception("Pets-feed warning callback failed")


def save_pets(cards: list[PetCard], path: str | Path = DEFAULT_PETS_PATH) -> None:
    """Write the feed atomically (tmp file + replace), mirroring save_redirects."""
    pets_path = Path(path)
    temporary_path = pets_path.with_name(f"{pets_path.name}.tmp")
    with temporary_path.open("w", encoding="utf-8") as pets_file:
        json.dump(cards, pets_file, indent=2)
        pets_file.write("\n")
    temporary_path.replace(pets_path)
