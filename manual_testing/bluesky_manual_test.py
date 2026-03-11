import sys
import os
import random

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from adoption_sources import SourceRescueGroups
from social_posters.bluesky import PosterBluesky


def main():
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


if __name__ == "__main__":
    main()