import argparse
import sys
import os
import random

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from abstractions import Post
from adoption_sources import SourceRescueGroups
from social_posters.bluesky import PosterBluesky


GLANDIS_ADOPTION_URL = (
    "https://www.smalldogrescuene.org/adoptable-dogs/"
    "#action_0=pet&animalID_0=22537020&petIndex_0=-1"
)
GLANDIS_IMAGE_URL = (
    "https://cdn.bsky.app/img/feed_fullsize/plain/"
    "did:plc:mbzwl5ssmltfls4dkmm2t6dj/"
    "bafkreiaslmsxrbsz77txaxyxqav2cgilpebjvrxkygbkfmnktohnedncgm"
)


def _publish(post: Post) -> None:
    poster = PosterBluesky()

    if not poster.authenticate():
        print("Authentication failed!")
        exit(1)

    print("Authenticated to Bluesky!")
    print(f"\nPost preview:\n{post.text}")
    print(f"\nTags: {post.tags}")

    result = poster.publish(post)

    if result.success:
        print(f"\nPosted successfully! URL: {result.post_url}")
    else:
        print(f"\nPost failed: {result.error_message}")
        exit(1)


def repost_glandis() -> None:
    post = Post(
        text=(
            "Hi, I'm Glandis in TX! I'm a Chihuahua / Mixed (short coat) "
            "in Cranston, RI.\n\n"
            "8 Months - Female - Small size\n\n"
            f"Adopt me: {GLANDIS_ADOPTION_URL}"
        ),
        image_url=GLANDIS_IMAGE_URL,
        link=GLANDIS_ADOPTION_URL,
        alt_text=(
            "Photo of Glandis in TX, a Chihuahua / Mixed (short coat) "
            "available for adoption"
        ),
        tags=["AdoptDontShop", "Boston", "Cranston", "DogsOfBluesky"],
    )
    _publish(post)


def post_random_rescuegroups_pet() -> None:
    poster = PosterBluesky()

    if not poster.authenticate():
        print("Authentication failed!")
        exit(1)

    print("Authenticated to Bluesky!")

    source = SourceRescueGroups()
    pets = list(source.fetch_pets())
    print(f"Fetched {len(pets)} pets")

    with_images = [p for p in pets if p.image_url]
    if not with_images:
        print("No pets with images found.")
        exit(1)

    pet = random.choice(with_images)
    print(f"Selected: {pet.name}")

    post = poster.format_post(pet)
    print(f"\nPost preview:\n{post.text}")
    print(f"\nTags: {post.tags}")

    result = poster.publish(post)

    if result.success:
        print(f"\nPosted successfully! URL: {result.post_url}")
    else:
        print(f"\nPost failed: {result.error_message}")
        exit(1)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repost-glandis", action="store_true")
    args = parser.parse_args()

    if args.repost_glandis:
        repost_glandis()
    else:
        post_random_rescuegroups_pet()


if __name__ == "__main__":
    main()