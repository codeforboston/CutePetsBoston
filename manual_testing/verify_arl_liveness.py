"""Verify the ARL 24PetConnect liveness fallback against real data.

Fetches three ARL pets by id -- one currently live on 24PetConnect and two
that have been removed (but may still be listed on RescueGroups) -- and prints
the adoption_url that SourceRescueGroups._parse_animal produces. Expected:

  * live pet   -> keeps the 24petconnect.com deep link
  * removed pet -> falls back to the arlboston.org org page (no 500 link)

READ-ONLY (posts nothing). Needs CUTEPETSBOSTON_RESCUEGROUPS_API_KEY.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from adoption_sources.rescue_groups import SourceRescueGroups, _session_with_retries

BASE_URL = "https://api.rescuegroups.org/v5/public/animals"

# (pet_id, expected-liveness) -- from the scan; ARABELLA is live, the others gone.
CANDIDATES = [
    ("22628355", "live (A300563 / ARABELLA)"),
    ("22605662", "removed (A299778 / CARLY)"),
    ("22605661", "removed (A282786 / GREG)"),
]


def _fetch(session, pet_id, api_key, src):
    url = f"{BASE_URL}/{pet_id}?include=orgs"
    headers = {"Content-Type": "application/vnd.api+json", "Authorization": api_key}
    resp = session.get(url, headers=headers, timeout=30)
    if resp.status_code == 404:
        return None
    resp.raise_for_status()
    body = resp.json()
    data = body.get("data")
    if not data:
        return None
    animal = data[0] if isinstance(data, list) else data
    orgs_by_id = {
        item["id"]: item.get("attributes", {})
        for item in body.get("included", [])
        if item.get("type") == "orgs"
    }
    return src._parse_animal(animal, orgs_by_id)


def main():
    api_key = os.environ.get("CUTEPETSBOSTON_RESCUEGROUPS_API_KEY")
    if not api_key:
        raise SystemExit("CUTEPETSBOSTON_RESCUEGROUPS_API_KEY not set.")

    session = _session_with_retries()
    src = SourceRescueGroups(api_key=api_key)

    failures = 0
    for pet_id, note in CANDIDATES:
        pet = _fetch(session, pet_id, api_key, src)
        if pet is None:
            print(f"[SKIP] {pet_id} ({note}): no record returned (fully delisted).")
            continue
        url = pet.adoption_url or ""
        is_deep = "24petconnect.com" in url
        expect_deep = note.startswith("live")
        ok = is_deep == expect_deep
        failures += 0 if ok else 1
        print(f"[{'OK' if ok else 'FAIL'}] {pet.name} ({note})")
        print(f"      adoption_url = {url}")
        print(f"      -> {'24PetConnect deep link' if is_deep else 'org-page fallback'}"
              f" (expected {'deep link' if expect_deep else 'fallback'})\n")

    if failures:
        raise SystemExit(f"{failures} case(s) did not behave as expected.")
    print("Liveness fallback behaves correctly.")


if __name__ == "__main__":
    main()
