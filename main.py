import os
import random

def main():
    sources = create_sources()
    posters = create_posters(debug=False)

    run(sources, posters)


def create_posters(debug=False):
    if debug:
        from social_posters.debug import PosterDebug

        return [PosterDebug()]

    requested_platforms = _requested_platforms()
    poster_factories = {
        "bluesky": _load_bluesky_poster,
        "instagram": _load_instagram_poster,
        "mastodon": _load_mastodon_poster,
    }

    if requested_platforms:
        return [
            poster_factories[platform_name]()
            for platform_name in poster_factories
            if platform_name in requested_platforms
        ]

    return [factory() for factory in poster_factories.values()]


def create_sources():
    from adoption_sources import SourceRescueGroups

    sources = []

    sources.append(SourceRescueGroups())

    return sources


def run(sources, posters):
    pets = []
    for source in sources:
        try:
            pets.extend(list(source.fetch_pets()))
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


def _requested_platforms():
    raw_value = os.environ.get("POSTER_PLATFORMS", "")
    if not raw_value.strip():
        return set()

    return {
        platform.strip().lower()
        for platform in raw_value.split(",")
        if platform.strip()
    }


def _load_bluesky_poster():
    from social_posters.bluesky import PosterBluesky

    return PosterBluesky()


def _load_instagram_poster():
    from social_posters.instagram import PosterInstagram

    return PosterInstagram()


def _load_mastodon_poster():
    from social_posters.mastodon import PosterMastodon

    return PosterMastodon()


if __name__ == "__main__":
    main()
