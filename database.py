import json
import traceback
import logging

from pathlib import Path

logger = logging.getLogger(__name__)


def read_database(database_path):
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


def write_database(database_path, data):
    path = Path(database_path)
    temporary_path = path.with_name(f"{path.name}.tmp")
    with temporary_path.open("w") as database_file:
        json.dump(data, database_file, indent=4)
    temporary_path.replace(path)
