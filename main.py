import random

def main():
    sources = create_sources()
    posters = create_posters(debug=False)

    run(sources, posters)


def create_posters(debug=False):
    from social_posters import PosterDebug

    if debug:
        return [PosterDebug()]

    from social_posters.instagram import PosterInstagram
    from social_posters.bluesky import PosterBluesky

    posters = []
    posters.append(PosterBluesky())
    posters.append(PosterInstagram())
    return posters


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


if __name__ == "__main__":
    main()
