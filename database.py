import json
import logging
import traceback
from pathlib import Path
from typing import NotRequired, TypedDict, cast

logger = logging.getLogger(__name__)


class PostedPet(TypedDict):
    name: str
    pet_id: str | None
    posted_at: str


class MetricSnapshot(TypedDict):
    collected_at: str
    likes: int | None
    reposts: int | None
    comments: int | None


class PublishedPost(TypedDict):
    pet_id: str | None
    platform: str
    post_id: str | None
    post_url: NotRequired[str | None]
    posted_at: str
    metrics: NotRequired[list[MetricSnapshot]]


class Database(TypedDict, total=False):
    posted_pets: list[PostedPet]
    posts: list[PublishedPost]


def read_database(database_path: str | Path) -> Database:
    path = Path(database_path)
    if not path.exists() or path.stat().st_size == 0:
        return {}

    try:
        with path.open() as database_file:
            # The existing database is trusted here; this cast does not validate JSON.
            return cast(Database, json.load(database_file))
    except (json.JSONDecodeError, ValueError) as exc:
        logger.error("%s:%s", type(exc).__name__, exc)
        traceback.print_exc()
        return {}


def write_database(database_path: str | Path, data: Database) -> None:
    path = Path(database_path)
    temporary_path = path.with_name(f"{path.name}.tmp")
    with temporary_path.open("w") as database_file:
        json.dump(data, database_file, indent=4)
    temporary_path.replace(path)
