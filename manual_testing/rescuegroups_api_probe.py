"""Fetch live cat data with Requests, then curl if the first transport fails."""

import json
import os
import subprocess
from pathlib import Path

import requests

URL = (
    "https://api.rescuegroups.org/v5/public/animals/search/available/haspic"
    "?include=orgs,breeds,locations,species,pictures&sort=random&limit=250"
)


def main():
    api_key = os.environ.get("CUTEPETSBOSTON_RESCUEGROUPS_API_KEY")
    if not api_key:
        raise SystemExit("RescueGroups API key is not set.")
    payload = {
        "data": {
            "filters": [{"fieldName": "species.singular", "operation": "equals", "criteria": "Cat"}],
            "filterProcessing": "1",
            "filterRadius": {"miles": 50, "postalcode": "02108"},
        }
    }
    response_path = Path("rescuegroups-cats.json")
    try:
        response = requests.post(
            URL,
            headers={"Content-Type": "application/vnd.api+json", "Authorization": api_key},
            json=payload,
            timeout=(10, 30),
        )
        print(f"Requests HTTP status: {response.status_code}", flush=True)
        response.raise_for_status()
        body = response.json()
        transport = "Requests"
    except (requests.RequestException, ValueError) as exc:
        print(f"Requests failed ({type(exc).__name__}); comparing curl.", flush=True)
        payload_path = Path("rescuegroups-cat-query.json")
        payload_path.write_text(json.dumps(payload), encoding="utf-8")
        # Pass the key over stdin, never through command arguments or output.
        result = subprocess.run(
            [
                "curl",
                "--silent",
                "--show-error",
                "--fail-with-body",
                "--connect-timeout",
                "10",
                "--max-time",
                "40",
                "--header",
                "@-",
                "--data-binary",
                f"@{payload_path}",
                "--output",
                str(response_path),
                "--write-out",
                "%{http_code}",
                URL,
            ],
            input=f"Content-Type: application/vnd.api+json\nAuthorization: {api_key}\n",
            text=True,
            capture_output=True,
            check=False,
        )
        print(f"curl exit code: {result.returncode}; HTTP status: {result.stdout}", flush=True)
        if result.returncode:
            response_path.unlink(missing_ok=True)
            raise SystemExit("Both direct API transports failed; no post will be attempted.")
        body = json.loads(response_path.read_text(encoding="utf-8"))
        transport = "curl"
    if not isinstance(body, dict) or not isinstance(body.get("data"), list) or not body["data"]:
        response_path.unlink(missing_ok=True)
        raise SystemExit("The API returned no usable cat records; no post will be attempted.")
    response_path.write_text(json.dumps(body), encoding="utf-8")
    print(f"Fetched {len(body['data'])} live cat records using {transport}.")
    for animal in body["data"][:5]:
        attrs = animal.get("attributes", {})
        print(json.dumps({"id": animal.get("id"), "name": attrs.get("name"), "breed": attrs.get("breedString")}))


if __name__ == "__main__":
    main()
