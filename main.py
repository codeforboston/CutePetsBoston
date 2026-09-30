import argparse
import json
import logging
import os
import pprint
import random
import sys
import traceback
from collections.abc import Iterable
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import cast

import requests

from abstractions import (
    AdoptablePet,
    MetricCollector,
    MetricsProvider,
    NamedPlatform,
    PetProvider,
    PetSource,
    PostPublisher,
    PostResult,
    SocialPoster,
)
from adoption_sources import SourceManual, SourceRescueGroups
from database import MetricSnapshot, read_database, write_database
from metric_collectors.bluesky import CollectorBluesky
from metric_collectors.instagram import CollectorInstagram
from metric_collectors.mastodon import CollectorMastodon
from metrics_dashboard import dashboard
from social_posters.bluesky import PosterBluesky
from social_posters.debug import PosterDebug
from social_posters.instagram import PosterInstagram
from social_posters.mastodon import PosterMastodon

file_handler = logging.FileHandler("cutepets.log")
file_handler.setLevel(logging.DEBUG)
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.INFO)

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[file_handler, console_handler],
)

logger = logging.getLogger(__name__)


def main() -> None:
    logger.info("Log started")
    parser = argparse.ArgumentParser()
    parser.add_argument("--debugsources", action="store_true")  # this defaults to False
    parser.add_argument("--debugposters", action="store_true")  # this defaults to False

    args = parser.parse_args()

    try:
        sources = create_sources(debug=args.debugsources)
        posters = create_posters(debug=args.debugposters)
        collectors = create_collectors(debug=args.debugposters)

        run(sources, posters, collectors)
    except Exception:
        notify_slack_of_exception(traceback.format_exc())
        raise


def create_posters(debug: bool = False) -> list[SocialPoster]:
    if debug:
        return [PosterDebug()]

    return [PosterMastodon(), PosterBluesky(), PosterInstagram()]


def create_collectors(debug: bool = False) -> list[MetricCollector]:
    if debug:
        return []

    return [CollectorBluesky(), CollectorMastodon(), CollectorInstagram()]


def create_sources(debug: bool = False) -> list[PetSource]:
    if debug:
        cat_fixture_path = (
            Path(__file__).parent / "tests" / "fixtures" / "sample_cats.json"
        )
        with cat_fixture_path.open() as fixture_file:
            cat_animals = json.load(fixture_file)
        return [
            SourceManual(species="dog"),
            SourceManual(species="cat", animals=cat_animals),
        ]

    return [SourceRescueGroups()]


def run(
    sources: Iterable[PetProvider],
    posters: Iterable[PostPublisher],
    collectors: Iterable[MetricsProvider] | None = None,
    database_path: str | Path = "database.json",
) -> list[PostResult]:
    pets: list[AdoptablePet] = []
    for source in sources:
        try:
            pets.extend(list(source.fetch_pets()))
        except ValueError as exc:
            raise SystemExit(str(exc)) from exc

    logger.info("Fetched %d records", len(pets))
    pet = pick_pet(pets, database_path=database_path)
    results: list[PostResult] = []

    if not pet:
        logger.error("No pets available to post.")
    else:
        logger.info("Picked pet %s", pprint.pformat(pet))
        results, published_results = publish_posts(pet, posters)
        record_publish_results(pet, published_results, database_path=database_path)

    collect_metrics(collectors or [], database_path=database_path)
    dashboard(database_path=database_path)
    return results


def publish_posts(
    pet: AdoptablePet, posters: Iterable[PostPublisher]
) -> tuple[list[PostResult], list[tuple[PostPublisher, PostResult]]]:
    results: list[PostResult] = []
    published_results: list[tuple[PostPublisher, PostResult]] = []

    if not posters:
        logger.error("No social media credentials set; skipping post.")
    else:
        for poster in posters:
            post = poster.format_post(pet)
            result = poster.publish(post)
            results.append(result)
            published_results.append((poster, result))
            if not result.success:
                logger.error(
                    "%s post failed: %s",
                    poster.platform_name,
                    result.error_message,
                )
            else:
                logger.info("%s post published.", poster.platform_name)

    return results, published_results


def pick_pet(
    pets: Iterable[AdoptablePet], database_path: str | Path = "database.json"
) -> AdoptablePet:
    data = read_database(database_path)
    posted_pet_ids = {
        posted_pet["pet_id"] for posted_pet in data.get("posted_pets", [])
    }
    eligible = [
        pet
        for pet in pets
        if pet.image_urls and pet.adoption_url and pet.pet_id not in posted_pet_ids
    ]
    if not eligible:
        raise ValueError("No eligible pet found")

    return random.choice(eligible)


def record_publish_results(
    pet: AdoptablePet,
    results: Iterable[tuple[NamedPlatform, PostResult]],
    database_path: str | Path = "database.json",
) -> None:
    data = read_database(database_path)
    posted_pets = data.setdefault("posted_pets", [])
    posts = data.setdefault("posts", [])
    posted_at = datetime.now(timezone.utc).isoformat()

    posted_pets.append({"name": pet.name, "pet_id": pet.pet_id, "posted_at": posted_at})
    for poster, result in results:
        if not result.success:
            continue
        posts.append(
            {
                "pet_id": pet.pet_id,
                "platform": poster.platform_name,
                "post_id": result.post_id,
                "post_url": result.post_url,
                "posted_at": posted_at,
                "metrics": [],
            }
        )

    cutoff = datetime.now(timezone.utc) - timedelta(weeks=12)
    data["posted_pets"] = [
        item
        for item in posted_pets
        if datetime.fromisoformat(item["posted_at"]) >= cutoff
    ]
    data["posts"] = [
        item for item in posts if datetime.fromisoformat(item["posted_at"]) >= cutoff
    ]
    write_database(database_path, data)


def collect_metrics(
    collectors: Iterable[MetricsProvider],
    database_path: str | Path = "database.json",
    window_days: int = 14,
) -> None:
    try:
        data = read_database(database_path)
        posts = data.get("posts", [])
        if not posts:
            return

        collectors_by_platform = {
            collector.platform_name: collector for collector in collectors
        }
        cutoff = datetime.now(timezone.utc) - timedelta(days=window_days)
        updated = False

        for entry in posts:
            try:
                if datetime.fromisoformat(entry["posted_at"]) < cutoff:
                    continue

                collector = collectors_by_platform.get(entry.get("platform"))
                if collector is None:
                    continue

                metrics = collector.fetch_metrics(
                    # Collectors declare string IDs, but existing records permit
                    # null. Preserve forwarding those values without coercion
                    # or filtering; each collector retains its error handling.
                    cast(str, entry["post_id"]),
                    entry.get("post_url"),
                )
                if metrics is None:
                    continue

                snapshot: MetricSnapshot = {
                    "collected_at": datetime.now(timezone.utc).isoformat(),
                    "likes": metrics.likes,
                    "reposts": metrics.reposts,
                    "comments": metrics.comments,
                }
                entry.setdefault("metrics", []).append(snapshot)
                updated = True
            except Exception as exc:
                platform = entry.get("platform", "unknown platform")
                post_id = entry.get("post_id", "unknown post")
                logger.error(
                    "%s metric collection failed for %s: %s",
                    platform,
                    post_id,
                    exc,
                )

        if updated:
            write_database(database_path, data)
    except Exception as exc:
        logger.error("Metric collection failed: %s", exc)


# Slack incoming-webhook messages have a ~40k-char limit; cap the traceback
# well below that so the post stays readable and is never rejected.
MAX_TRACEBACK_CHARS = 2500


def notify_slack_of_exception(traceback_text: str) -> None:
    logger.info(traceback_text)

    webhook_url = os.environ.get("SLACK_WEBHOOK_URL")
    if not webhook_url:
        logger.warning("SLACK_WEBHOOK_URL not set; skipping Slack alert.")
        return

    app_env = os.environ.get("APP_ENV", "local")
    workflow = os.environ.get("GITHUB_WORKFLOW", "local run")
    event = os.environ.get("GITHUB_EVENT_NAME")
    repo = os.environ.get("GITHUB_REPOSITORY")
    run_id = os.environ.get("GITHUB_RUN_ID")
    run_link = (
        f"https://github.com/{repo}/actions/runs/{run_id}" if repo and run_id else None
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
        logger.error("Failed to post Slack alert: %s", slack_exc)


if __name__ == "__main__":
    main()
