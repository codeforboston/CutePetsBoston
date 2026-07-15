"""Scan the live RescueGroups feed for specific orgs.

A normal run samples 25 random pets and posts one, so a given small org almost
never shows up. This pages through the WHOLE in-radius feed (dogs + cats) and
reports, for each org we're trying to deep-link:

  * whether it appears at all within the radius,
  * the real ``rescueId`` / ``adoptionUrl`` its records carry, and
  * the URL ``reconstruct_adoption_url`` produces (so we can eyeball correctness).

Needs CUTEPETSBOSTON_RESCUEGROUPS_API_KEY. Radius/limit overridable via env:

    RG_RADIUS_MILES=150 python manual_testing/rescuegroups_org_scan.py
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import requests

from adoption_sources.pet_links import _domain_of, reconstruct_adoption_url
from adoption_sources.rescue_groups import SourceRescueGroups, _session_with_retries
from config import POSTAL_CODE

BASE_URL = "https://api.rescuegroups.org/v5/public/animals/search"

# Orgs we want to deep-link (matched by domain). wagtopia.com is included so we
# can see whether the Wagtopia orgs already ship a usable adoptionUrl.
TARGET_DOMAINS = {
    "pugrescueofnewengland.org",
    "paw-affectionrescue.org",
    "arlboston.org",
    "lasthopek9.org",
    "assweetasapeachanimalrescue.org",
    "wagtopia.com",
}

RADIUS_MILES = int(os.environ.get("RG_RADIUS_MILES", "50"))
PAGE_LIMIT = int(os.environ.get("RG_PAGE_LIMIT", "100"))
MAX_PAGES = int(os.environ.get("RG_MAX_PAGES", "25"))


def _fetch_page(species, page, api_key):
    url = (
        f"{BASE_URL}/available/{species}/haspic"
        f"?include=orgs&sort=animals.name&limit={PAGE_LIMIT}&page={page}"
    )
    headers = {"Content-Type": "application/vnd.api+json", "Authorization": api_key}
    payload = {"data": {"filterRadius": {"miles": RADIUS_MILES, "postalcode": POSTAL_CODE}}}
    resp = _session_with_retries().post(url, json=payload, headers=headers, timeout=30)
    resp.raise_for_status()
    return resp.json()


def scan():
    api_key = os.environ.get("CUTEPETSBOSTON_RESCUEGROUPS_API_KEY")
    if not api_key:
        raise SystemExit("CUTEPETSBOSTON_RESCUEGROUPS_API_KEY not set.")

    hits = {d: [] for d in TARGET_DOMAINS}
    total = 0

    for species in ("dogs", "cats"):
        src = SourceRescueGroups(api_key=api_key, species=species)
        page = 1
        while page <= MAX_PAGES:
            body = _fetch_page(species, page, api_key)
            data = body.get("data", [])
            if not data:
                break
            orgs_by_id = {
                item["id"]: item.get("attributes", {})
                for item in body.get("included", [])
                if item.get("type") == "orgs"
            }
            for animal in data:
                total += 1
                attrs = animal.get("attributes", {})
                org_id = (
                    animal.get("relationships", {}).get("orgs", {}).get("data", [{}])[0].get("id")
                )
                org_attrs = orgs_by_id.get(org_id, {}) if org_id else {}
                candidates = (attrs.get("adoptionUrl"), org_attrs.get("adoptionUrl"), org_attrs.get("url"))
                for url in candidates:
                    dom = _domain_of(url)
                    if dom in hits:
                        pet = src._parse_animal(animal, orgs_by_id)
                        hits[dom].append({
                            "name": attrs.get("name"),
                            "pet_id": animal.get("id"),
                            "rescueId": attrs.get("rescueId"),
                            "api_adoptionUrl": attrs.get("adoptionUrl"),
                            "org_url": org_attrs.get("url"),
                            "reconstructed": reconstruct_adoption_url(candidates, animal.get("id"), attrs.get("rescueId")),
                            "final_adoption_url": pet.adoption_url if pet else None,
                        })
                        break
            meta_pages = body.get("meta", {}).get("pages")
            if meta_pages is not None and page >= meta_pages:
                break
            page += 1

    print(f"Scanned {total} pets within {RADIUS_MILES} miles of {POSTAL_CODE}.\n")
    for dom in sorted(TARGET_DOMAINS):
        records = hits[dom]
        if not records:
            print(f"[MISSING] {dom}: not found in radius (widen RG_RADIUS_MILES, or org not on RescueGroups).")
            continue
        print(f"[FOUND]   {dom}: {len(records)} pet(s)")
        for r in records[:3]:
            print(f"    name={r['name']!r} pet_id={r['pet_id']} rescueId={r['rescueId']!r}")
            print(f"      api_adoptionUrl = {r['api_adoptionUrl']}")
            print(f"      reconstructed   = {r['reconstructed']}")
            print(f"      final_url       = {r['final_adoption_url']}")
        print()


if __name__ == "__main__":
    scan()
