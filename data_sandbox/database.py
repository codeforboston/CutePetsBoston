import io
import json
import logging
import traceback
import urllib.request
import zipfile
from pathlib import Path
import pandas as pd
import requests


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
