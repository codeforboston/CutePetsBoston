"""Bluesky-only deep-link test.

Posts one crafted pet per newly-supported org to the Bluesky TEST account, each
carrying the *reconstructed* deep link (built by ``reconstruct_adoption_url`` --
the same code production uses). This deterministically exercises the Bluesky
link-preservation path, which the random live feed rarely reaches for these orgs.

Dry run (build + validate, no network)::

    python manual_testing/bluesky_deeplink_test.py

Publish to the Bluesky test account (needs BLUESKY_HANDLE / BLUESKY_PASSWORD)::

    python manual_testing/bluesky_deeplink_test.py --publish
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from abstractions import AdoptablePet
from adoption_sources.pet_links import reconstruct_adoption_url
from social_posters.bluesky import PosterBluesky

# A public placeholder image so publish() has something to upload.
SAMPLE_IMAGE = "https://picsum.photos/seed/cutepets/800/600"

# (org landing url, pet_id, rescue_id) mirrors what the RescueGroups API gives us;
# reconstruct_adoption_url turns it into the org's deep link exactly as in prod.
SAMPLE_PETS = [
    # org label,        landing url,                                  pet_id,      rescue_id, name,     breed,           location
    ("Pug Rescue NE",   "https://pugrescueofnewengland.org/",         "22607616",  None,      "Waffles", "Pug",          "Boston, MA"),
    ("PAW Affection",   "https://www.paw-affectionrescue.org/",       "22606695",  None,      "Biscuit", "Beagle Mix",   "Boston, MA"),
    ("ARL Boston",      "https://www.arlboston.org/adopt/adopt-a-pet/","22999999",  "A300071", "Clover",  "Domestic Shorthair", "Boston, MA"),
    # SmallDog control -- already supported, longest URL, proves regression-safe.
    ("SmallDog (ctrl)", "https://www.smalldogrescuene.org/",          "22537020",  None,      "Glandis", "Chihuahua / Mixed (short coat)", "Cranston, RI"),
]


def build_pets():
    pets = []
    for label, landing, pet_id, rescue_id, name, breed, location in SAMPLE_PETS:
        url = reconstruct_adoption_url([landing], pet_id, rescue_id)
        if not url:
            raise SystemExit(
                f"[{label}] reconstruct_adoption_url returned None -- template not matched. "
                "The deep-link template for this org is missing or the id key is wrong."
            )
        species = "cat" if "shorthair" in breed.lower() else "dog"
        pets.append((label, url, AdoptablePet(
            name=name,
            species=species,
            breed=breed,
            location=location,
            description="Friendly, house-trained, and ready for a forever home. " * 4,
            adoption_url=url,
            image_url=SAMPLE_IMAGE,
            age_string="2 years",
            sex="Female",
            size_group="Small",
            pet_id=pet_id,
            rescue_id=rescue_id,
        )))
    return pets


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--publish", action="store_true",
                        help="Actually post to the Bluesky test account.")
    args = parser.parse_args()

    poster = PosterBluesky()

    if args.publish and not poster.authenticate():
        raise SystemExit("Bluesky authentication failed (check BLUESKY_HANDLE / BLUESKY_PASSWORD).")

    failures = 0
    for label, url, pet in build_pets():
        post = poster.format_post(pet)
        text, facets = poster._build_text_and_facets(post)
        link_facets = [f for f in facets if f["features"][0]["$type"] == "app.bsky.richtext.facet#link"]

        url_intact = url in text
        within_limit = len(text) <= 300
        has_link_facet = len(link_facets) == 1 and link_facets[0]["features"][0]["uri"] == url
        ok = url_intact and within_limit and has_link_facet

        print(f"\n===== {label} =====")
        print(f"Deep link : {url}")
        print(f"--- post text ({len(text)} chars) ---\n{text}")
        print(f"url intact: {url_intact} | <=300: {within_limit} | clickable link facet: {has_link_facet}")

        if not ok:
            failures += 1
            print("  !! VALIDATION FAILED")
            continue

        if args.publish:
            result = poster.publish(post)
            if result.success:
                print(f"  posted -> {result.post_url}")
            else:
                failures += 1
                print(f"  !! PUBLISH FAILED: {result.error_message}")

    if failures:
        raise SystemExit(f"\n{failures} case(s) failed.")
    print("\nAll deep-link cases passed.")


if __name__ == "__main__":
    main()
