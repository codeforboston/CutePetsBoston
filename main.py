import argparse
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
import json
import logging
import os
from pathlib import Path
import pprint
import random
import sqlite3
import sys
import traceback

import requests

from adoption_sources import SourceManual, SourceRescueGroups
from metric_collectors.bluesky import CollectorBluesky
from metric_collectors.instagram import CollectorInstagram
from metric_collectors.mastodon import CollectorMastodon
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


def main():
    logger.info("Log started")
    parser = argparse.ArgumentParser()
    parser.add_argument("--debugsources", action="store_true")
    parser.add_argument("--debugposters", action="store_true")

    args = parser.parse_args()

    try:
        sources = create_sources(debug=args.debugsources)
        posters = create_posters(debug=args.debugposters)
        collectors = create_collectors(debug=args.debugposters)

        run(sources, posters, collectors)
    except Exception:
        notify_slack_of_exception(traceback.format_exc())
        raise


def create_posters(debug=False):
    if debug:
        return [PosterDebug()]

    return [PosterMastodon(), PosterBluesky(), PosterInstagram()]


def create_collectors(debug=False):
    if debug:
        return []

    return [CollectorBluesky(), CollectorMastodon(), CollectorInstagram()]


def create_sources(debug=False):
    if debug:
        cat_fixture_path = Path(__file__).parent / "tests" / "fixtures" / "sample_cats.json"
        with cat_fixture_path.open() as fixture_file:
            cat_animals = json.load(fixture_file)
        return [
            SourceManual(species="dog"),
            SourceManual(species="cat", animals=cat_animals),
        ]

    return [SourceRescueGroups()]


def run(sources, posters, collectors=None, database_path="database.json", metrics_db_path="metrics.sqlite"):
    _init_metrics_db(metrics_db_path)

    pets = []
    for source in sources:
        try:
            pets.extend(list(source.fetch_pets()))
        except ValueError as exc:
            raise SystemExit(str(exc)) from exc

    logger.info("Fetched %d records", len(pets))
    pet = pick_pet(pets, database_path=database_path)
    results = []
    publish_results = []

    if not pet:
        logger.error("No pets available to post.")
    else:
        logger.info("Picked pet %s", pprint.pformat(pet))

        if not posters:
            logger.error("No social media credentials set; skipping post.")
        else:
            for poster in posters:
                post = poster.format_post(pet)
                result = poster.publish(post)
                results.append(result)
                publish_results.append((poster, result))
                if not result.success:
                    logger.error(
                        "%s post failed: %s",
                        poster.platform_name,
                        result.error_message,
                    )
                else:
                    logger.info("%s post published.", poster.platform_name)

        record_publish_results(pet, publish_results, database_path=database_path, metrics_db_path=metrics_db_path)

    collect_metrics(collectors or [], database_path=database_path, metrics_db_path=metrics_db_path)
    return results


def pick_pet(pets, database_path="database.json"):
    data = _read_database(database_path)
    posted_pet_ids = {
        posted_pet["pet_id"] for posted_pet in data.get("posted_pets", [])
    }
    eligible = [
        pet
        for pet in pets
        if pet.image_url
        and pet.adoption_url
        and pet.pet_id not in posted_pet_ids
    ]
    if not eligible:
        raise ValueError("No eligible pet found")

    return random.choice(eligible)


def record_publish_results(pet, results, database_path="database.json", metrics_db_path="metrics.sqlite"):
    data = _read_database(database_path)
    posted_pets = data.setdefault("posted_pets", [])
    posts = data.setdefault("posts", [])
    posted_at = datetime.now(timezone.utc).isoformat()

    posted_pets.append(
        {"name": pet.name, "pet_id": pet.pet_id, "posted_at": posted_at}
    )
    new_posts = []
    for poster, result in results:
        if not result.success:
            continue
        post_entry = {
            "pet_id": pet.pet_id,
            "platform": poster.platform_name,
            "post_id": result.post_id,
            "post_url": result.post_url,
            "posted_at": posted_at,
            "metrics": [],
        }
        posts.append(post_entry)
        new_posts.append(post_entry)

    cutoff = datetime.now(timezone.utc) - timedelta(weeks=12)
    data["posted_pets"] = [
        item
        for item in posted_pets
        if datetime.fromisoformat(item["posted_at"]) >= cutoff
    ]
    data["posts"] = [
        item
        for item in posts
        if datetime.fromisoformat(item["posted_at"]) >= cutoff
    ]
    _write_database(database_path, data)

    if new_posts:
        _upsert_posts_to_db(new_posts, metrics_db_path)


def collect_metrics(collectors, database_path="database.json", metrics_db_path="metrics.sqlite", window_days=14):
    try:
        data = _read_database(database_path)
        posts = data.get("posts", [])
        if not posts:
            return

        _init_metrics_db(metrics_db_path)
        _upsert_posts_to_db(posts, metrics_db_path)

        collectors_by_platform = {
            collector.platform_name: collector for collector in collectors
        }
        cutoff = datetime.now(timezone.utc) - timedelta(days=window_days)
        updated = False

        with sqlite3.connect(metrics_db_path) as conn:
            for entry in posts:
                try:
                    if datetime.fromisoformat(entry["posted_at"]) < cutoff:
                        continue

                    collector = collectors_by_platform.get(entry.get("platform"))
                    if collector is None:
                        continue

                    metrics = collector.fetch_metrics(
                        entry["post_id"], entry.get("post_url")
                    )
                    if metrics is None:
                        continue

                    snapshot = asdict(metrics)
                    collected_at = datetime.now(timezone.utc).isoformat()
                    snapshot["collected_at"] = collected_at
                    entry.setdefault("metrics", []).append(snapshot)
                    updated = True
                    conn.execute(
                        """
                        INSERT INTO post_metrics (post_id, collected_at, likes, reposts, comments)
                        VALUES (?, ?, ?, ?, ?)
                        """,
                        (
                            entry["post_id"],
                            collected_at,
                            snapshot.get("likes"),
                            snapshot.get("reposts"),
                            snapshot.get("comments"),
                        ),
                    )
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
            _write_database(database_path, data)
    except Exception as exc:
        logger.error("Metric collection failed: %s", exc)


def _init_metrics_db(metrics_db_path):
    with sqlite3.connect(metrics_db_path) as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pet_id TEXT NOT NULL,
                platform TEXT NOT NULL,
                post_id TEXT NOT NULL UNIQUE,
                post_url TEXT NOT NULL,
                posted_at TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                updated_at TEXT NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS post_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                post_id TEXT NOT NULL,
                collected_at TEXT NOT NULL,
                likes INTEGER,
                reposts INTEGER,
                comments INTEGER,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                updated_at TEXT NOT NULL DEFAULT (datetime('now')),
                FOREIGN KEY (post_id) REFERENCES posts (post_id)
            );
        """)


def _upsert_posts_to_db(posts, metrics_db_path):
    with sqlite3.connect(metrics_db_path) as conn:
        conn.executemany(
            """
            INSERT INTO posts (pet_id, platform, post_id, post_url, posted_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(post_id) DO UPDATE SET
                updated_at = datetime('now')
            """,
            [
                (
                    post["pet_id"],
                    post["platform"],
                    post["post_id"],
                    post["post_url"],
                    post["posted_at"],
                )
                for post in posts
            ],
        )


def _read_database(database_path):
    path = Path(database_path)
    if not path.exists() or path.stat().st_size == 0:
        return {}

    try:
        with path.open() as database_file:
            return json.load(database_file)
    except (json.JSONDecodeError, ValueError) as exc:
        logger.error("%s:%s", type(exc).__name__, exc)
        traceback.print_exc()
        return {}


def _write_database(database_path, data):
    path = Path(database_path)
    temporary_path = path.with_name(f"{path.name}.tmp")
    with temporary_path.open("w") as database_file:
        json.dump(data, database_file, indent=4)
    temporary_path.replace(path)


# Slack incoming-webhook messages have a ~40k-char limit; cap the traceback
# well below that so the post stays readable and is never rejected.
MAX_TRACEBACK_CHARS = 2500


def notify_slack_of_exception(traceback_text):
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
        logger.error("Failed to post Slack alert: %s", slack_exc)


if __name__ == "__main__":
    main()
