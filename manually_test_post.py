"""Manual CLI for exercising poster implementations with sample pet data.

Examples:
  python manually_test_post.py --poster instagram --username USER --password PASS
  python manually_test_post.py --poster bluesky --username USER --password PASS
"""

import argparse
import sys

from abstractions import AdoptablePet
from poster_bluesky import PosterBluesky
from poster_instagram import PosterInstagram


def sample_pet():
    sample = {
        "attributes": {
            "name": "Doli",
            "breedString": "Husky / Shepherd / Mixed",
            "descriptionText": (
                "Hi hoomans, my name is Doli, and I'm in the prime of my life at about 11-years-old. "
                "Everyone comments on my sky blue eyes and thick husky-type hair that is every shade of gold you can imagine. "
                "At 50 lbs, I am a fit and healthy girl.\n\n"
                "I am very chill and quiet. That doesn't mean I don't get excited because I do! "
                "When the hoomans come home, I do a fun little wiggle dance to welcome them! "
                "I LOVE being outside and like going on walks and car rides.\n\n"
                "Hope to meet you soon! Doli"
            ),
            "pictureThumbnailUrl": "https://cdn.rescuegroups.org/8099/pictures/animals/10131/10131543/35520048.jpg?width=100",
            "slug": "adopt-doli-husky-dog",
        }
    }
    attrs = sample["attributes"]
    return AdoptablePet(
        name=attrs["name"],
        species="dog",
        breed=attrs["breedString"],
        location="Boston, MA",
        description=attrs["descriptionText"],
        adoption_url=f"https://www.rescuegroups.org/pet/{attrs['slug']}",
        image_url=attrs["pictureThumbnailUrl"],
    )


def build_poster(poster, username, password):
    if poster == "instagram":
        return PosterInstagram(username, password)
    if poster == "bluesky":
        return PosterBluesky(username, password)
    raise ValueError(f"Unsupported poster: {poster}")


def main():
    parser = argparse.ArgumentParser(
        description="Manually post a sample adoptable pet using a poster implementation."
    )
    parser.add_argument("--poster", choices=["instagram", "bluesky"], required=True)
    parser.add_argument("--username", required=True)
    parser.add_argument("--password", required=True)
    args = parser.parse_args()

    poster = build_poster(args.poster, args.username, args.password)
    pet = sample_pet()
    post = poster.format_post(pet)
    result = poster.publish(post)
    if not result.success:
        print(f"{poster.platform_name} post failed: {result.error_message}")
        return 1
    print(f"{poster.platform_name} post published.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
