"""Read-only pass inspector for the CutePetsBoston posting pipeline.

This script is intentionally separate from production orchestration. It calls
pure production transformations where possible, records each stage, and avoids
calling functions that publish posts or mutate database.json.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass, is_dataclass
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Iterable

import requests

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from abstractions import AdoptablePet, Post, SocialPoster
from adoption_sources.rescue_groups import SourceRescueGroups
from main import create_posters


@dataclass(frozen=True)
class InspectionStage:
    name: str
    data: Any


class InspectionRecorder:
    def __init__(self) -> None:
        self.stages: list[InspectionStage] = []

    def record(self, name: str, data: Any) -> None:
        self.stages.append(InspectionStage(name=name, data=data))

    def to_json(self) -> str:
        return json.dumps(_to_jsonable(self.stages), indent=2, ensure_ascii=False)

    def render_text(self) -> str:
        chunks = []
        for stage in self.stages:
            chunks.append(f"\n{'=' * 72}\n{stage.name}\n{'=' * 72}")
            chunks.append(json.dumps(_to_jsonable(stage.data), indent=2, ensure_ascii=False))
        return "\n".join(chunks).lstrip()


def inspect_rescuegroups_pipeline(
    *,
    source: SourceRescueGroups,
    posters: Iterable[SocialPoster],
    database_path: Path = Path("database.json"),
    http_client=requests,
    sample_size: int | None = 10,
) -> InspectionRecorder:
    """Inspect the live RescueGroups-to-post flow without publishing or writing.

    Args:
        source: Configured RescueGroups source. The source API key is used for
            the request but is never recorded in inspection output.
        posters: Poster instances whose formatters should be inspected.
        database_path: Posted-pet database to read. The file is not created or
            modified.
        http_client: requests-like object used for tests.
        sample_size: Maximum number of per-record entries to print per stage.
            Pass None to include all records.
    """
    recorder = InspectionRecorder()

    recorder.record("source.config", _source_config(source))

    request = _build_rescuegroups_request(source)
    recorder.record("fetch.request", _request_snapshot(request))

    response = _post_rescuegroups_request(request, http_client=http_client)
    body = response["body"]
    recorder.record(
        "fetch.response",
        {
            "status_code": response["status_code"],
            "data_count": len(body.get("data", [])),
            "included_count": len(body.get("included", [])),
            "animals": _limit_items(
                [_animal_summary(animal) for animal in body.get("data", [])],
                sample_size,
            ),
        },
    )

    parsed_records, parsed_pets = _parse_animals(source, body)
    recorder.record("parse.animals", _limit_items(parsed_records, sample_size))

    filter_records, filtered_pets = _filter_placeholders(source, parsed_pets)
    recorder.record("filter.placeholder", _limit_items(filter_records, sample_size))

    database_snapshot = _read_posted_database(database_path)
    recorder.record("eligibility.database_snapshot", database_snapshot)

    eligibility_records, eligible_pets = _inspect_eligibility(
        filtered_pets,
        posted_pet_ids=set(database_snapshot["posted_pet_ids"]),
    )
    recorder.record(
        "eligibility.result",
        {
            "eligible_count": len(eligible_pets),
            "records": _limit_items(eligibility_records, sample_size),
        },
    )

    recorder.record(
        "select.preview",
        {
            "candidate_count": len(eligible_pets),
            "selection_policy": "Production pick_pet randomly chooses one candidate.",
            "read_only": True,
            "candidates": _limit_items(
                [_pet_snapshot(pet) for pet in eligible_pets],
                sample_size,
            ),
        },
    )

    format_records = _inspect_formatters(posters, eligible_pets, sample_size)
    recorder.record("format.posts", format_records)

    return recorder


def _source_config(source: SourceRescueGroups) -> dict[str, Any]:
    return {
        "source_name": source.source_name,
        "base_url": source.BASE_URL,
        "postal_code": source.postal_code,
        "radius_miles": source.radius_miles,
        "species": source.species,
        "limit": source.limit,
        "location_label": source.location_label,
        "has_api_key": bool(source._api_key),
    }


def _build_rescuegroups_request(source: SourceRescueGroups) -> dict[str, Any]:
    if not source._api_key:
        raise ValueError(
            "RescueGroups API key not configured. "
            "Set CUTEPETSBOSTON_RESCUEGROUPS_API_KEY environment variable."
        )

    url = (
        f"{source.BASE_URL}/available/{source.species}/haspic"
        f"?include=orgs,breeds,locations"
        f"&sort=random"
        f"&limit={source.limit}"
    )
    headers = {
        "Content-Type": "application/vnd.api+json",
        "Authorization": source._api_key,
    }
    payload = {
        "data": {
            "filterRadius": {
                "miles": source.radius_miles,
                "postalcode": source.postal_code,
            }
        }
    }
    return {"url": url, "headers": headers, "json": payload, "timeout": 30}


def _request_snapshot(request: dict[str, Any]) -> dict[str, Any]:
    headers = dict(request["headers"])
    if "Authorization" in headers:
        headers["Authorization"] = "<redacted>"
    return {
        "method": "POST",
        "url": request["url"],
        "headers": headers,
        "json": request["json"],
        "timeout": request["timeout"],
    }


def _post_rescuegroups_request(
    request: dict[str, Any],
    *,
    http_client: Any,
) -> dict[str, Any]:
    response = http_client.post(
        request["url"],
        json=request["json"],
        headers=request["headers"],
        timeout=request["timeout"],
    )
    response.raise_for_status()
    return {
        "status_code": getattr(response, "status_code", None),
        "body": response.json(),
    }


def _parse_animals(
    source: SourceRescueGroups,
    body: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[AdoptablePet]]:
    orgs_by_id = {
        item["id"]: item.get("attributes", {})
        for item in body.get("included", [])
        if item.get("type") == "orgs"
    }

    records = []
    pets = []
    for animal in body.get("data", []):
        pet = source._parse_animal(animal, orgs_by_id)
        records.append(
            {
                "input": _animal_summary(animal),
                "output": _pet_snapshot(pet) if pet else None,
                "parsed": pet is not None,
            }
        )
        if pet:
            pets.append(pet)

    return records, pets


def _filter_placeholders(
    source: SourceRescueGroups,
    pets: list[AdoptablePet],
) -> tuple[list[dict[str, Any]], list[AdoptablePet]]:
    records = []
    kept = []
    for pet in pets:
        is_placeholder = source._is_placeholder_name(pet.name)
        records.append(
            {
                "pet_id": pet.pet_id,
                "name": pet.name,
                "keep": not is_placeholder,
                "reason": "placeholder_name" if is_placeholder else None,
            }
        )
        if not is_placeholder:
            kept.append(pet)
    return records, kept


def _read_posted_database(database_path: Path) -> dict[str, Any]:
    if not database_path.exists():
        return {
            "path": str(database_path),
            "exists": False,
            "read_only": True,
            "posted_count": 0,
            "posted_pet_ids": [],
            "expired_count": 0,
            "json_error": None,
        }

    try:
        with database_path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
    except (json.JSONDecodeError, ValueError) as exc:
        return {
            "path": str(database_path),
            "exists": True,
            "read_only": True,
            "posted_count": 0,
            "posted_pet_ids": [],
            "expired_count": 0,
            "json_error": f"{type(exc).__name__}: {exc}",
        }

    posted = data.get("posted_pets", [])
    posted_pet_ids = sorted(
        str(item["pet_id"])
        for item in posted
        if isinstance(item, dict) and item.get("pet_id") is not None
    )
    cutoff = datetime.now(timezone.utc) - timedelta(weeks=12)
    expired_count = 0
    for item in posted:
        if not isinstance(item, dict) or not item.get("posted_at"):
            continue
        try:
            if datetime.fromisoformat(item["posted_at"]) <= cutoff:
                expired_count += 1
        except ValueError:
            continue

    return {
        "path": str(database_path),
        "exists": True,
        "read_only": True,
        "posted_count": len(posted),
        "posted_pet_ids": posted_pet_ids,
        "expired_count": expired_count,
        "note": "Current pick_pet checks all posted IDs before pruning old rows.",
        "json_error": None,
    }


def _inspect_eligibility(
    pets: list[AdoptablePet],
    *,
    posted_pet_ids: set[str],
) -> tuple[list[dict[str, Any]], list[AdoptablePet]]:
    records = []
    eligible = []
    for pet in pets:
        checks = {
            "has_image_url": bool(pet.image_url),
            "has_adoption_url": bool(pet.adoption_url),
            "not_already_posted": str(pet.pet_id) not in posted_pet_ids,
        }
        reasons = [name for name, passed in checks.items() if not passed]
        keep = not reasons
        records.append(
            {
                "pet_id": pet.pet_id,
                "name": pet.name,
                "keep": keep,
                "checks": checks,
                "skip_reasons": reasons,
            }
        )
        if keep:
            eligible.append(pet)
    return records, eligible


def _inspect_formatters(
    posters: Iterable[SocialPoster],
    pets: list[AdoptablePet],
    sample_size: int | None,
) -> list[dict[str, Any]]:
    records = []
    for pet in _limit_items(pets, sample_size):
        for poster in posters:
            try:
                post = poster.format_post(pet)
                records.append(
                    {
                        "pet_id": pet.pet_id,
                        "pet_name": pet.name,
                        "platform": poster.platform_name,
                        "post": _post_snapshot(post),
                        "publish_payload_preview": _publish_payload_preview(
                            poster,
                            post,
                        ),
                    }
                )
            except Exception as exc:
                records.append(
                    {
                        "pet_id": pet.pet_id,
                        "pet_name": pet.name,
                        "platform": poster.platform_name,
                        "error": f"{type(exc).__name__}: {exc}",
                    }
                )
    return records


def _publish_payload_preview(poster: SocialPoster, post: Post) -> dict[str, Any]:
    preview: dict[str, Any] = {
        "would_publish": False,
        "requires_image": poster.platform_name in {"Mastodon", "Instagram"},
        "has_image": bool(post.image_url),
    }

    if poster.platform_name == "Mastodon" and hasattr(poster, "_format_caption_thread"):
        main_caption, replies = poster._format_caption_thread(post)
        preview["mastodon"] = {
            "main_caption": main_caption,
            "main_caption_chars": len(main_caption),
            "reply_count": len(replies),
            "replies": replies,
            "reply_chars": [len(reply) for reply in replies],
        }
    elif poster.platform_name == "Bluesky" and hasattr(poster, "_build_text_and_facets"):
        text, facets = poster._build_text_and_facets(post)
        preview["bluesky"] = {
            "record_text": text,
            "record_text_chars": len(text),
            "facets": facets,
            "would_embed_image": bool(post.image_url),
        }
    elif poster.platform_name == "Instagram" and hasattr(poster, "_format_caption"):
        caption = poster._format_caption(post)
        preview["instagram"] = {
            "caption": caption,
            "caption_chars": len(caption),
            "image_url": post.image_url,
        }

    return preview


def _animal_summary(animal: dict[str, Any]) -> dict[str, Any]:
    attrs = animal.get("attributes", {})
    org_relationship = (
        animal.get("relationships", {})
        .get("orgs", {})
        .get("data", [])
    )
    return {
        "id": animal.get("id"),
        "type": animal.get("type"),
        "name": attrs.get("name"),
        "breedString": attrs.get("breedString"),
        "breedPrimary": attrs.get("breedPrimary"),
        "has_descriptionText": bool(attrs.get("descriptionText")),
        "descriptionText_chars": len(attrs.get("descriptionText") or ""),
        "has_adoptionUrl": bool(attrs.get("adoptionUrl")),
        "has_pictureThumbnailUrl": bool(attrs.get("pictureThumbnailUrl")),
        "org_ids": [item.get("id") for item in org_relationship],
    }


def _pet_snapshot(pet: AdoptablePet | None) -> dict[str, Any] | None:
    if pet is None:
        return None
    return {
        "name": pet.name,
        "species": pet.species,
        "breed": pet.breed,
        "location": pet.location,
        "description": pet.description,
        "description_chars": len(pet.description or ""),
        "adoption_url": pet.adoption_url,
        "image_url": pet.image_url,
        "age_string": pet.age_string,
        "sex": pet.sex,
        "size_group": pet.size_group,
        "pet_id": pet.pet_id,
    }


def _post_snapshot(post: Post) -> dict[str, Any]:
    return {
        "text": post.text,
        "text_chars": len(post.text),
        "image_url": post.image_url,
        "link": post.link,
        "alt_text": post.alt_text,
        "tags": post.tags,
    }


def _limit_items(items: list[Any], sample_size: int | None) -> list[Any]:
    if sample_size is None:
        return items
    return items[:sample_size]


def _to_jsonable(value: Any) -> Any:
    if is_dataclass(value):
        return _to_jsonable(asdict(value))
    if isinstance(value, list):
        return [_to_jsonable(item) for item in value]
    if isinstance(value, tuple):
        return [_to_jsonable(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _to_jsonable(item) for key, item in value.items()}
    return value


def _sample_size_arg(value: str) -> int | None:
    if value == "all":
        return None
    parsed = int(value)
    if parsed < 0:
        raise argparse.ArgumentTypeError("sample size must be non-negative or 'all'")
    return parsed


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Inspect the RescueGroups posting pipeline without publishing.",
    )
    parser.add_argument("--limit", type=int, default=25)
    parser.add_argument("--radius-miles", type=int, default=50)
    parser.add_argument("--species", default="dogs", choices=("dogs", "cats"))
    parser.add_argument("--database-path", type=Path, default=Path("database.json"))
    parser.add_argument(
        "--sample-size",
        type=_sample_size_arg,
        default=10,
        help="records to print per stage, or 'all'",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="render structured JSON instead of text sections",
    )
    args = parser.parse_args(argv)

    source = SourceRescueGroups(
        radius_miles=args.radius_miles,
        species=args.species,
        limit=args.limit,
    )
    recorder = inspect_rescuegroups_pipeline(
        source=source,
        posters=create_posters(debug=False),
        database_path=args.database_path,
        sample_size=args.sample_size,
    )
    output = recorder.to_json() if args.json else recorder.render_text()
    print(output)
    return 0


if __name__ == "__main__":
    sys.exit(main())
