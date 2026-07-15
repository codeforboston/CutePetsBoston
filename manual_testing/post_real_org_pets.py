"""Post one REAL pet from each of the 3 deep-link orgs to Bluesky.

Fetches live RescueGroups pets, keeps only those whose adoption_url was
reconstructed into a per-pet deep link for Pug Rescue NE / PAW Affection /
ARL Boston (and that have an image), and posts one per org via PosterBluesky.

These are genuine adoptable pets, so this is safe to run against the live
@CutePetsBoston account -- it's essentially a targeted manual prod post whose
point is to eyeball that the reconstructed deep links render full + clickable.

    python manual_testing/post_real_org_pets.py            # dry-run (no posting)
    python manual_testing/post_real_org_pets.py --publish  # actually post
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from adoption_sources.pet_links import _domain_of
from adoption_sources.rescue_groups import SourceRescueGroups, _session_with_retries
from config import POSTAL_CODE
from social_posters.bluesky import PosterBluesky

BASE_URL = "https://api.rescuegroups.org/v5/public/animals"

# Candidate pet_ids per org, from the read-only scan. We fetch these by ID
# (a few light GETs) instead of paging the whole feed -- paging hammers the
# API and trips its per-key rate limit. First candidate with an image wins.
ORG_CANDIDATES = {
    "Pug Rescue NE": ["22358386", "22553438", "22284739"],
    "PAW Affection": ["22606695", "22606720"],
    "ARL Boston": ["22628355", "22605662", "22605661"],
}


def _fetch_animal(session, pet_id, api_key, src):
    """GET one animal by id; return an AdoptablePet or None (adopted/gone)."""
    url = f"{BASE_URL}/{pet_id}?include=orgs"
    headers = {"Content-Type": "application/vnd.api+json", "Authorization": api_key}
    resp = session.get(url, headers=headers, timeout=30)
    if resp.status_code == 404:
        return None
    resp.raise_for_status()
    body = resp.json()
    data = body.get("data")
    if not data:
        return None
    animal = data[0] if isinstance(data, list) else data
    orgs_by_id = {
        item["id"]: item.get("attributes", {})
        for item in body.get("included", [])
        if item.get("type") == "orgs"
    }
    return src._parse_animal(animal, orgs_by_id)


def collect_one_per_org(api_key):
    """Return {label: AdoptablePet} with one postable pet per target org."""
    picked = {}
    session = _session_with_retries()
    src = SourceRescueGroups(api_key=api_key)  # only used for _parse_animal
    cat_hints = ("shorthair", "longhair", "tabby", "domestic short", "domestic long",
                 "siamese", "tuxedo", "calico", "maine coon")
    for label, candidates in ORG_CANDIDATES.items():
        for pet_id in candidates:
            pet = _fetch_animal(session, pet_id, api_key, src)
            if pet and pet.image_url and pet.adoption_url:
                # by-id GET isn't species-scoped; correct the label from the breed.
                if any(h in (pet.breed or "").lower() for h in cat_hints):
                    pet.species = "cat"
                picked[label] = pet
                break
    return picked


def _web_url(post_uri, handle):
    # at://did/app.bsky.feed.post/<rkey> -> https://bsky.app/profile/<handle>/post/<rkey>
    if not post_uri:
        return None
    rkey = post_uri.rstrip("/").split("/")[-1]
    return f"https://bsky.app/profile/{handle}/post/{rkey}"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--publish", action="store_true", help="Actually post to Bluesky.")
    args = parser.parse_args()

    api_key = os.environ.get("CUTEPETSBOSTON_RESCUEGROUPS_API_KEY")
    if not api_key:
        raise SystemExit("CUTEPETSBOSTON_RESCUEGROUPS_API_KEY not set.")

    poster = PosterBluesky()
    if args.publish and not poster.authenticate():
        raise SystemExit("Bluesky authentication failed (check BLUESKY_HANDLE / BLUESKY_PASSWORD).")

    picked = collect_one_per_org(api_key)
    if not picked:
        raise SystemExit("Found no pets from the target orgs in the current feed.")

    missing = [lbl for lbl in ORG_CANDIDATES if lbl not in picked]
    if missing:
        print(f"NOTE: no current pet found for: {', '.join(missing)}\n")

    failures = 0
    for label, pet in picked.items():
        post = poster.format_post(pet)
        text, facets = poster._build_text_and_facets(post)
        link_ok = any(
            f["features"][0]["$type"] == "app.bsky.richtext.facet#link"
            and f["features"][0]["uri"] == pet.adoption_url
            for f in facets
        )
        print(f"===== {label}: {pet.name} =====")
        print(f"Deep link : {pet.adoption_url}")
        print(f"--- post text ({len(text)} chars) ---\n{text}")
        print(f"link intact + clickable facet: {pet.adoption_url in text and link_ok}\n")

        if args.publish:
            result = poster.publish(post)
            if result.success:
                print(f"  POSTED -> {_web_url(result.post_url, poster.username)}\n")
            else:
                failures += 1
                print(f"  !! PUBLISH FAILED: {result.error_message}\n")

    if failures:
        raise SystemExit(f"{failures} post(s) failed.")
    print("Done." + ("" if args.publish else " (dry-run; pass --publish to post)"))


if __name__ == "__main__":
    main()
