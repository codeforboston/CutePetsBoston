"""Refresh saved adoption statuses without publishing social posts."""

import argparse
import logging
import os
from collections.abc import Sequence
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote

import requests

from database import PostedPet, read_database, write_database

BASE_URL = "https://api.rescuegroups.org/v5/public/animals"
logger = logging.getLogger(__name__)


def _is_due(pet: PostedPet, now: datetime) -> bool:
    if not str(pet.get("pet_id") or "").strip() or pet.get("status_name", "").casefold() == "adopted":
        return False
    checked_at = pet.get("status_checked_at")
    if not checked_at:
        return True
    checked = datetime.fromisoformat(checked_at)
    missing_since = pet.get("status_missing_since")
    weekly = missing_since and checked - datetime.fromisoformat(missing_since) >= timedelta(days=7)
    return now - checked >= timedelta(days=7 if weekly else 1)


def _resources(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, dict):
        return [value]
    if value is None:
        return []
    if isinstance(value, list) and all(isinstance(item, dict) for item in value):
        return value
    raise ValueError("Invalid resource data")


def _fetch_status(session: requests.Session, pet_id: str, status_names: dict[str, str]) -> tuple[str, str] | None:
    response = session.get(f"{BASE_URL}/{quote(pet_id, safe='')}", params={"include": "statuses"}, timeout=30)
    if response.status_code == 404:
        return None
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, dict) or "data" not in payload:
        raise ValueError("Invalid animal response")
    animal = next((item for item in _resources(payload["data"]) if str(item.get("id")) == pet_id), None)
    if animal is None:
        return None
    links = _resources(animal["relationships"]["statuses"]["data"])
    if not links or links[0].get("id") is None:
        raise ValueError("Status ID unavailable")
    status_id = str(links[0]["id"])
    if status_id in status_names:
        return status_id, status_names[status_id]
    status = next(
        (
            item
            for item in _resources(payload.get("included"))
            if item.get("type") == "statuses" and str(item.get("id")) == status_id
        ),
        {},
    )
    name = status.get("attributes", {}).get("name")
    if not isinstance(name, str) or not name.strip():
        response = session.get(f"{BASE_URL}/statuses/{quote(status_id, safe='')}", timeout=30)
        response.raise_for_status()
        status = next((item for item in _resources(response.json()["data"]) if str(item.get("id")) == status_id), {})
        name = status.get("attributes", {}).get("name")
    if not isinstance(name, str) or not name.strip():
        raise ValueError("Status name unavailable")
    status_names[status_id] = name.strip()
    return status_id, status_names[status_id]


def refresh_statuses(
    database_path: str | Path,
    *,
    session: requests.Session,
    now: datetime | None = None,
) -> None:
    now = now or datetime.now(timezone.utc)
    data = read_database(database_path)
    updated = False
    status_names: dict[str, str] = {}
    for pet in data.get("posted_pets", []):
        if not _is_due(pet, now):
            continue
        updated = True
        pet["status_checked_at"] = now.isoformat()
        try:
            status = _fetch_status(session, str(pet["pet_id"]).strip(), status_names)
            if status:
                pet["status_id"], pet["status_name"] = status
                pet["status_observed_at"] = now.isoformat()
                pet.pop("status_missing_since", None)
            else:
                pet.setdefault("status_missing_since", now.isoformat())
        except (requests.RequestException, ValueError, KeyError, TypeError, AttributeError) as exc:
            pet.pop("status_missing_since", None)
            logger.warning("Status lookup failed for %s: %s", pet["pet_id"], type(exc).__name__)
    if updated:
        write_database(database_path, data)


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database-path", type=Path, default=Path("database.json"))
    args = parser.parse_args(argv)
    api_key = os.environ.get("CUTEPETSBOSTON_RESCUEGROUPS_API_KEY", "").strip()
    if not api_key:
        parser.error("CUTEPETSBOSTON_RESCUEGROUPS_API_KEY is required")
    logging.basicConfig(level=logging.INFO)
    with requests.Session() as session:
        session.headers.update({"Authorization": api_key, "Content-Type": "application/vnd.api+json"})
        refresh_statuses(args.database_path, session=session)


if __name__ == "__main__":
    main()
