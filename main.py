import os
import random
import argparse
import json
import sys
import traceback
import logging
from pathlib import Path
from datetime import datetime, timezone, timedelta

import requests

logger = logging.getLogger(__name__)

def main():
    logging.basicConfig(filename='cutepets.log', level=logging.DEBUG)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)
    logger.addHandler(console_handler)
    logger.debug('Log started')
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
    Path("database.json").touch(exist_ok=True)
    # Open file
    with open("database.json", "r+") as f:
        # Load json
        try:
            data = json.load(f)
        except (json.JSONDecodeError, ValueError) as e:
            print(f"{type(e).__name__}:{e}", file=sys.stderr)
            traceback.print_exc()
            data = {}
        
        if "posted_pets" in data:
            posted_pet_ids =  {posted_pet["pet_id"] for posted_pet in data["posted_pets"]}
        else:
            posted_pet_ids = {}
            data["posted_pets"] = []
        # Check pet has an image, adoption url, and has not been posted
        eligible = [pet for pet in pets if pet.image_url and pet.adoption_url and pet.pet_id not in posted_pet_ids]
        if not eligible:
            raise ValueError("No elligible pet found")
        
        selected_pet = random.choice(eligible)
        # Add pet ID to list of posted pets
        data["posted_pets"].append({"name": selected_pet.name, "pet_id": selected_pet.pet_id, "posted_at": datetime.now(timezone.utc).isoformat()})
        # Remove old pets
        cutoff = datetime.now(timezone.utc) - timedelta(weeks=12)
        recent_pets = [item for item in data["posted_pets"] if datetime.fromisoformat(item['posted_at']) > cutoff]
        data["posted_pets"] = recent_pets
        # Export json
        f.seek(0)
        json.dump(data, f, indent=4)
        f.truncate()
        return selected_pet


# Slack incoming-webhook messages have a ~40k-char limit; cap the traceback
# well below that so the post stays readable and is never rejected.
MAX_TRACEBACK_CHARS = 2500


def notify_slack_of_exception(traceback_text):
    print(traceback_text)

    webhook_url = os.environ.get("SLACK_WEBHOOK_URL")
    if not webhook_url:
        print("SLACK_WEBHOOK_URL not set; skipping Slack alert.")
        return

    app_env = os.environ.get("APP_ENV", "local")
    workflow = os.environ.get("GITHUB_WORKFLOW", "local run")
    event = os.environ.get("GITHUB_EVENT_NAME")
    repo = os.environ.get("GITHUB_REPOSITORY")
    run_id = os.environ.get("GITHUB_RUN_ID")
    run_link = (
        f"https://github.com/{repo}/actions/runs/{run_id}"
        if repo and run_id
        else None
    )

    header = f"CutePetsBoston [{app_env}] run failed in *{workflow}*"
    if event:
        header += f" (trigger: {event})"
    if run_link:
        header += f" (<{run_link}|view run>)"
    text = f"{header}\n```{traceback_text.strip()[-MAX_TRACEBACK_CHARS:]}```"

    try:
        response = requests.post(webhook_url, json={"text": text}, timeout=10)
        response.raise_for_status()
    except Exception as slack_exc:
        print(f"Failed to post Slack alert: {slack_exc}")


if __name__ == "__main__":
    main()
