#curl -X POST "https://mastodon.social/api/v1/statuses" \
#  -H "Authorization: Bearer h_o6jBz37M5322Mb8a1PYNTA9ALjfKL15_XMY2dYwAs" \
#  -H "Content-Type: application/json" \
#  -d '{"status": "Hello from my dev app! 🚀"}'

# RESET TOKEN LATER!!!

import sys
import os
import random

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from adoption_sources import SourceRescueGroups
from social_posters.mastodon import PosterMastodon

def main():
    poster = PosterMastodon()

    if not poster.authenticate():
        print("Authentication failed!")
        exit(1)

    print("Authenticated to Mastodon!")

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
