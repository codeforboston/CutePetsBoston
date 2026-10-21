"""Preview a currently adoptable cat; pass --publish to post it to Bluesky.

Run from the repository root:
    python3 manual_testing/bluesky_cat_manual_test.py
    python3 manual_testing/bluesky_cat_manual_test.py --publish

Requires CUTEPETSBOSTON_RESCUEGROUPS_API_KEY. Publishing also requires
BLUESKY_HANDLE and BLUESKY_PASSWORD for the intended account.
"""

import argparse
import json
import os
import random
import sys
import time
from pathlib import Path

import requests

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from adoption_sources import SourceRescueGroups
from social_posters.bluesky import PosterBluesky


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--publish", action="store_true", help="Publish one real Bluesky post")
    args = parser.parse_args()

    poster = PosterBluesky()
    if args.publish and not (poster.username and poster.password):
        raise SystemExit("Set BLUESKY_HANDLE and BLUESKY_PASSWORD for the intended account first.")

    pets = [
        pet
        for pet in SourceRescueGroups(species=("cats",)).fetch_pets()
        if pet.species == "cat" and pet.image_urls and pet.adoption_url
    ]
    if not pets:
        raise SystemExit("No currently available cats with photos and adoption links found.")

    pet = random.choice(pets)
    post = poster.format_post(pet)
    text, _ = poster._build_text_and_facets(post)
    print(f"Cat: {pet.name} (RescueGroups ID: {pet.pet_id})")
    print(f"Breed from API: {pet.breed!r}")
    print(f"Breed hashtags: {poster._cat_breed_tags(pet.breed)}")
    print(f"Character count: {len(text)}/300")
    print(f"\n{text}\n")

    if not args.publish:
        print("Preview only. Add --publish to fetch a cat and publish a real post.")
        return

    print(f"Publishing to {poster.username}...")
    result = poster.publish(post)
    if not result.success:
        raise SystemExit(f"Post failed: {result.error_message}")
    uri = result.post_url or ""
    record_key = uri.rsplit("/", 1)[-1]
    post_url = f"https://bsky.app/profile/{poster._did}/post/{record_key}"
    print(f"Posted successfully: {post_url}")
    print(f"Post URI: {uri}")

    report = {
        "pet_id": pet.pet_id,
        "breed": pet.breed,
        "expected_breed_tags": poster._cat_breed_tags(pet.breed),
        "post_url": post_url,
        "post_uri": uri,
        "text": text,
        "verified": False,
    }
    report_path = Path("cat-breed-live-result.json")
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_path:
        with open(summary_path, "a", encoding="utf-8") as summary:
            summary.write(f"Posted one cat: [View Bluesky post]({post_url})\n\n")

    # Read back the saved record directly; never retry publishing on a read failure.
    for attempt in range(5):
        try:
            response = requests.get(
                "https://bsky.social/xrpc/com.atproto.repo.getRecord",
                params={"repo": poster._did, "collection": "app.bsky.feed.post", "rkey": record_key},
                timeout=20,
            )
            response.raise_for_status()
            record = response.json()["value"]
            actual_tags = {
                feature["tag"]
                for facet in record.get("facets", [])
                for feature in facet.get("features", [])
                if feature.get("$type") == "app.bsky.richtext.facet#tag"
            }
            if record["text"] != text or not set(report["expected_breed_tags"]).issubset(actual_tags):
                raise ValueError("Saved post does not contain the expected text and breed hashtag facets")
            report["verified"] = True
            report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
            print("Verified the breed hashtags in the saved Bluesky post.")
            if summary_path:
                with open(summary_path, "a", encoding="utf-8") as summary:
                    summary.write(f"Verified breed hashtags: {', '.join(report['expected_breed_tags'])}\n")
            return
        except (requests.RequestException, KeyError, ValueError) as exc:
            if attempt == 4:
                raise
            print(f"Readback attempt {attempt + 1} failed: {exc}")
            time.sleep(2)


if __name__ == "__main__":
    main()
