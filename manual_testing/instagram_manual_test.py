import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from abstractions import AdoptablePet
from social_posters.instagram import PosterInstagram


def sample_pet():
    return AdoptablePet(
        name="Brian",
        species="dog",
        breed="Labrador Retriever",
        location="Boston, MA",
        description="Brian is a laid-back lab mix who loves a good nap and a good book.",
        adoption_url="https://example.org/adopt/brian",
        image_url="https://static.wikia.nocookie.net/familyguy/images/c/c2/FamilyGuy_Single_BrianWriter_R7.jpg/revision/latest?cb=20230807152447",
        age_string="4 years",
        sex="Male",
        size_group="Large",
        pet_id="manual-test-brian",
    )


testing_cases = [sample_pet]


def main():
    parser = argparse.ArgumentParser(
        description="Manually exercise the Instagram poster against a real account."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Format the post without authenticating or publishing.",
    )
    parser.add_argument(
        "--image-url",
        help="Override the sample pet's image URL with a different publicly accessible image.",
    )
    args = parser.parse_args()

    poster = PosterInstagram()

    if not args.dry_run and not poster.authenticate():
        print("Authentication failed!")
        sys.exit(1)

    if not args.dry_run:
        print(f"Authenticated to Instagram as @{poster.username}")

    for make_pet in testing_cases:
        pet = make_pet()
        if args.image_url:
            pet.image_url = args.image_url

        post = poster.format_post(pet)
        print(f"\nPost preview:\n{post.text}")
        print(f"\nTags: {post.tags}")
        print(f"Alt text: {post.alt_text}")

        if args.dry_run:
            continue

        print(
            "\nPublishing (this polls Instagram until the image finishes "
            "processing, up to 60s)..."
        )
        result = poster.publish(post)

        if result.success:
            print(f"\nPosted successfully! Media ID: {result.post_id}, URL: {result.post_url}")
        else:
            print(f"\nPost failed: {result.error_message}")
            sys.exit(1)


if __name__ == "__main__":
    main()
