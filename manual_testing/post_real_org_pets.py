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

BASE_URL = "https://api.rescuegroups.org/v5/public/animals/search"

# Reconstructed-URL domain -> label. ARL's deep link points at 24PetConnect.
TARGET_OUTPUT_DOMAINS = {
    "pugrescueofnewengland.org": "Pug Rescue NE",
    "paw-affectionrescue.org": "PAW Affection",
    "24petconnect.com": "ARL Boston",
}

RADIUS_MILES = int(os.environ.get("RG_RADIUS_MILES", "50"))
PAGE_LIMIT = 100
MAX_PAGES = 25


def _fetch_page(session, species, page, api_key):
    url = (
        f"{BASE_URL}/available/{species}/haspic"
        f"?include=orgs&sort=animals.name&limit={PAGE_LIMIT}&page={page}"
    )
    headers = {"Content-Type": "application/vnd.api+json", "Authorization": api_key}
    payload = {"data": {"filterRadius": {"miles": RADIUS_MILES, "postalcode": POSTAL_CODE}}}
    resp = session.post(url, json=payload, headers=headers, timeout=30)
    resp.raise_for_status()
    return resp.json()


def collect_one_per_org(api_key):
    """Return {label: AdoptablePet} with one postable pet per target org."""
    picked = {}
    # One pooled, retrying session for all pages -- avoids the connection resets
    # that a fresh session per page triggers under rapid paged POSTs.
    session = _session_with_retries()
    for species in ("dogs", "cats"):
        src = SourceRescueGroups(api_key=api_key, species=species)
        page = 1
        while page <= MAX_PAGES and len(picked) < len(TARGET_OUTPUT_DOMAINS):
            body = _fetch_page(session, species, page, api_key)
            data = body.get("data", [])
            if not data:
                break
            orgs_by_id = {
                item["id"]: item.get("attributes", {})
                for item in body.get("included", [])
                if item.get("type") == "orgs"
            }
            for animal in data:
                pet = src._parse_animal(animal, orgs_by_id)
                if not pet or not pet.image_url or not pet.adoption_url:
                    continue
                label = TARGET_OUTPUT_DOMAINS.get(_domain_of(pet.adoption_url))
                if label and label not in picked:
                    picked[label] = pet
            meta_pages = body.get("meta", {}).get("pages")
            if meta_pages is not None and page >= meta_pages:
                break
            page += 1
        if len(picked) == len(TARGET_OUTPUT_DOMAINS):
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

    missing = [lbl for lbl in TARGET_OUTPUT_DOMAINS.values() if lbl not in picked]
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
