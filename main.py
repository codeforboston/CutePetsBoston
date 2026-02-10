import os
import random
import sys

from abstractions import PosterDebug
from poster_bluesky import PosterBluesky
# from poster_instagram import PosterInstagram
from source_manual import SourceManual

def main():
    # TODO: inconsistently declaring os.env vars inside this file vs the classes. We
    # should decide what pattern is best
    source = SourceManual()
    posters = create_posters()

    run(source, posters)


def create_posters(debug=False):
    if debug:
        return [PosterDebug()]

    posters = []

    # Instagram has not been tested yet
    # instagram_username = os.environ.get("INSTAGRAM_USERNAME")
    # instagram_password = os.environ.get("INSTAGRAM_PASSWORD")
    # if instagram_username and instagram_password:
    #     posters.append(PosterInstagram(instagram_username, instagram_password))

    bluesky_username = os.environ.get("BLUESKY_HANDLE") or os.environ.get(
        "BLUESKY_TEST_HANDLE"
    )
    bluesky_password = os.environ.get("BLUESKY_PASSWORD") or os.environ.get(
        "BLUESKY_TEST_PASSWORD"
    )
    if bluesky_username and bluesky_password:
        posters.append(PosterBluesky(bluesky_username, bluesky_password))

    return posters


def run(source, posters):
    try:
        pets = list(source.fetch_pets())
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc

    print("Fetched", len(pets), "records")
    pet = pick_pet(pets)
    if not pet:
        print("No pets available to post.")
        print(pets)
        return []

    if not posters:
        print("No social media credentials set; skipping post.")
        return []

    results = []
    for poster in posters:
        post = poster.format_post(pet)
        result = poster.publish(post)
        results.append(result)
        if not result.success:
            print(f"{poster.platform_name} post failed: {result.error_message}")
        else:
            print(f"{poster.platform_name} post published.")

    return results

def pick_pet(pets):
    with_images = [pet for pet in pets if pet.image_url]
    if not with_images:
        return None
    return random.choice(with_images)



if __name__ == "__main__":
    main()
