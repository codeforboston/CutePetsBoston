import os
import random
import argparse
import traceback

import requests


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--debugsources", action="store_true") # this defaults to False
    parser.add_argument("--debugposters", action="store_true") # this defaults to False

    args = parser.parse_args()

    try:
        sources = create_sources(debug=args.debugsources)
        posters = create_posters(debug=args.debugposters)

        run(sources, posters)
    except Exception:
        notify_slack_of_exception(traceback.format_exc())
        raise


def notify_slack_of_exception(tb_text):
    webhook_url = os.environ.get("SLACK_WEBHOOK_URL")
    if not webhook_url:
        print("SLACK_WEBHOOK_URL not set; skipping Slack alert.")
        return

    workflow = os.environ.get("GITHUB_WORKFLOW", "local run")
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    run_id = os.environ.get("GITHUB_RUN_ID")
    run_link = (
        f"https://github.com/{repo}/actions/runs/{run_id}"
        if repo and run_id
        else None
    )

    header = f"CutePetsBoston run failed in *{workflow}*"
    if run_link:
        header += f" (<{run_link}|view run>)"
    text = f"{header}\n```{tb_text.strip()[-2500:]}```"

    try:
        response = requests.post(webhook_url, json={"text": text}, timeout=10)
        response.raise_for_status()
    except Exception as slack_exc:
        print(f"Failed to post Slack alert: {slack_exc}")


def create_posters(debug=False):
    from social_posters.debug import PosterDebug
    
    if debug:

        return [PosterDebug()]
    from social_posters.instagram import PosterInstagram
    from social_posters.bluesky import PosterBluesky
    from social_posters.mastodon import PosterMastodon

    posters = []
    posters.append(PosterMastodon())
    posters.append(PosterBluesky())
    posters.append(PosterInstagram())
    return posters




def create_sources(debug=False):
    from adoption_sources import SourceRescueGroups, SourceManual
    
    if debug:
        return [SourceManual()]

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
    eligible = [pet for pet in pets if pet.image_url and pet.adoption_url]
    if not eligible:
        return None
    return random.choice(eligible)




if __name__ == "__main__":
    main()
