"""Find adoptable pets, reconstruct their deep links, and (optionally) post to Bluesky.

This mirrors the intended bot behavior and doubles as a manual verification tool.

Two modes:
  * default: pick a pet from any *supported* shelter (Sterling / SmallDog) -- the
    ones we can build a working deep link for.
  * --shelters a.org,b.org: post one pet from EACH listed shelter domain, even if
    it isn't deep-linkable (useful to see what a fallback link looks like live,
    e.g. MSPCA).

Safe by default: a DRY RUN that only previews. Pass --post to actually publish.

Setup -- put these in a gitignored .env at the repo root (or export them)::

    CUTEPETSBOSTON_RESCUEGROUPS_API_KEY=...
    BLUESKY_HANDLE=<account handle>
    BLUESKY_PASSWORD=<account app password>

Usage (from repo root)::

    python manual_testing/verify_deep_links.py --post
    python manual_testing/verify_deep_links.py --post --shelters smalldogrescuene.org,mspca.org
"""

import argparse
import json
import os
import random
import re
import sys
from pathlib import Path

import requests

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from adoption_sources.pet_links import (  # noqa: E402
    PET_FINDER_TEMPLATES,
    _domain_of,
    is_supported_org,
)
from adoption_sources.rescue_groups import SourceRescueGroups  # noqa: E402
from social_posters.bluesky import PosterBluesky  # noqa: E402


def load_dotenv() -> None:
    """Minimal .env loader so we don't add a dependency for a manual script."""
    env_path = Path(__file__).resolve().parent.parent / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def matches_domain(url: str | None, domain: str) -> bool:
    d = _domain_of(url)
    return bool(d) and (d == domain or d.endswith("." + domain))


def collect_pets(max_pulls: int, limit: int, need_domains: list[str] | None):
    """Pull the API up to max_pulls times, deduping by pet_id.

    Stops early once we have what we need: a supported pet (need_domains None),
    or at least one pet for every requested domain.
    """
    all_by_id: dict[str, object] = {}
    for i in range(max_pulls):
        try:
            pets = list(SourceRescueGroups(limit=limit).fetch_pets())
        except Exception as exc:
            print(f"  pull {i + 1}: FAILED {type(exc).__name__}: {exc}", file=sys.stderr)
            continue
        for pet in pets:
            if pet.pet_id:
                all_by_id[pet.pet_id] = pet
        pool = list(all_by_id.values())
        if need_domains is None:
            satisfied = any(is_supported_org(p.adoption_url) for p in pool)
            note = f"{sum(is_supported_org(p.adoption_url) for p in pool)} supported"
        else:
            have = {d for d in need_domains if any(matches_domain(p.adoption_url, d) for p in pool)}
            satisfied = have == set(need_domains)
            note = f"have {sorted(have)} / need {need_domains}"
        print(f"  pull {i + 1}: {len(pets)} pets (total {len(pool)}); {note}")
        if satisfied:
            break
    return list(all_by_id.values())


def print_org_tally(all_pets) -> None:
    known = set(PET_FINDER_TEMPLATES)
    counts: dict[str, int] = {}
    for pet in all_pets:
        domain = _domain_of(pet.adoption_url) or "(none)"
        counts[domain] = counts.get(domain, 0) + 1
    print("\nShelter domains in this sample (★ = supported / deep-linkable):")
    for domain, n in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0])):
        base = domain[4:] if domain.startswith("www.") else domain
        star = "★" if base in known or any(base.endswith("." + k) for k in known) else " "
        print(f"  {star} {n:3d}  {domain}")


def post_pet(pet, do_post: bool) -> bool:
    """Preview a pet's Bluesky post and optionally publish it. Returns success."""
    poster = PosterBluesky()
    post = poster.format_post(pet)
    url = pet.adoption_url or ""
    deep = "#action_0=pet" in url or "mspca.org/pets/" in url
    print("\n" + "=" * 70)
    print(f"SELECTED: {pet.name}  [pet_id={pet.pet_id}]  ({pet.location})")
    label = "DEEP LINK (should open the pet)" if deep else "FALLBACK LINK (NOT pet-specific)"
    print(f"{label}:\n  {pet.adoption_url}")
    print("-" * 70)
    print(f"Bluesky post text:\n\n{post.text}")
    print(f"\nTags: {post.tags}\nImage: {post.image_url}")
    print("=" * 70)

    if not do_post:
        print("DRY RUN — not posted. Add --post to publish.")
        return True
    if not poster._is_available:
        print("Bluesky credentials not set (BLUESKY_HANDLE / BLUESKY_PASSWORD).", file=sys.stderr)
        return False
    print("Publishing to Bluesky...")
    result = poster.publish(post)
    if result.success:
        print(f"POSTED. post_url={result.post_url}")
        return True
    print(f"POST FAILED: {result.error_message}", file=sys.stderr)
    return False


def inspect_domain(domain: str, pulls: int, limit: int) -> None:
    """Dump the FULL raw RescueGroups record for pets from `domain`.

    Used to hunt for a shelter-internal id (e.g. MSPCA's `a467410`) that we'd
    need to build that shelter's deep link. Does not post anything.
    """
    src = SourceRescueGroups(limit=limit)
    url = (f"{src.BASE_URL}/available/{src.species}/haspic"
           f"?include=orgs,breeds,locations&sort=random&limit={limit}")
    headers = {"Content-Type": "application/vnd.api+json", "Authorization": src._api_key}
    payload = {"data": {"filterRadius": {"miles": src.radius_miles, "postalcode": src.postal_code}}}

    shown = 0
    for i in range(pulls):
        body = requests.post(url, json=payload, headers=headers, timeout=30).json()
        orgs = {it["id"]: it.get("attributes", {})
                for it in body.get("included", []) if it.get("type") == "orgs"}
        for animal in body.get("data", []):
            org_id = (animal.get("relationships", {}).get("orgs", {})
                      .get("data", [{}])[0].get("id"))
            org = orgs.get(org_id, {})
            if domain not in (org.get("url") or "") and domain not in (org.get("adoptionUrl") or ""):
                continue
            shown += 1
            print(f"\n===== {domain} pet (rescuegroups id={animal.get('id')}) =====")
            print("ANIMAL attributes:")
            print(json.dumps(animal.get("attributes", {}), indent=2)[:3000])
            print("ORG attributes:")
            print(json.dumps(org, indent=2)[:1500])
            blob = json.dumps(animal) + json.dumps(org)
            candidates = sorted(set(re.findall(r"a\d{4,8}", blob, flags=re.IGNORECASE)))
            print(f"Possible shelter-internal ids (a##### pattern): {candidates}")
            if shown >= 3:
                return
        print(f"  pull {i + 1}: {shown} {domain} pets dumped so far")
        if shown:
            return
    if not shown:
        print(f"No {domain} pets found in {pulls} pulls.")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--inspect", type=str, default="",
                        help="Dump raw API records for pets from this shelter domain "
                             "(e.g. mspca.org) and exit. Does not post.")
    parser.add_argument("--post", action="store_true",
                        help="Actually publish to Bluesky (default is a dry-run preview).")
    parser.add_argument("--shelters", type=str, default="",
                        help="Comma-separated shelter domains to post one pet from each "
                             "(e.g. smalldogrescuene.org,mspca.org). Default: any supported shelter.")
    parser.add_argument("--max-pulls", type=int, default=8,
                        help="Max random API pulls while searching (default 8).")
    parser.add_argument("--limit", type=int, default=100,
                        help="Pets per pull (default 100).")
    args = parser.parse_args()

    load_dotenv()
    if not os.environ.get("CUTEPETSBOSTON_RESCUEGROUPS_API_KEY"):
        print("CUTEPETSBOSTON_RESCUEGROUPS_API_KEY not set (put it in .env).", file=sys.stderr)
        return 1

    if args.inspect:
        inspect_domain(args.inspect, args.max_pulls, args.limit)
        return 0

    domains = [d.strip() for d in args.shelters.split(",") if d.strip()] or None
    print(f"Searching (up to {args.max_pulls} pulls)...")
    all_pets = collect_pets(args.max_pulls, args.limit, domains)
    print(f"\nDone: {len(all_pets)} distinct pets seen.")
    print_org_tally(all_pets)

    # Build the list of pets to post: one per requested domain, or one supported.
    targets = []
    if domains:
        for d in domains:
            candidates = [p for p in all_pets if matches_domain(p.adoption_url, d)]
            if candidates:
                targets.append((d, random.choice(candidates)))
            else:
                print(f"\n[{d}] no pet found in this sample.", file=sys.stderr)
    else:
        supported = [p for p in all_pets if is_supported_org(p.adoption_url)]
        if supported:
            targets.append(("supported", random.choice(supported)))

    if not targets:
        print("\nNo matching pet found. Try a higher --max-pulls.", file=sys.stderr)
        return 2

    all_ok = True
    for label, pet in targets:
        print(f"\n#### {label} ####")
        if not post_pet(pet, args.post):
            all_ok = False
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
