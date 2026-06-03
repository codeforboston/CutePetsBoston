"""Find a pet from a supported shelter, reconstruct its deep link, and (optionally)
post it to the Bluesky TEST account.

This mirrors the intended bot behavior: only pets from shelters we can build a
working deep link for (Sterling, SmallDog) are eligible. We pull the RescueGroups
API repeatedly (random order) until we find one, then reconstruct the link.

Safe by default: a DRY RUN that only previews. Pass --post to actually publish.

Setup -- put these in a gitignored .env at the repo root (or export them)::

    CUTEPETSBOSTON_RESCUEGROUPS_API_KEY=...
    BLUESKY_HANDLE=<your TEST account handle>
    BLUESKY_PASSWORD=<your TEST account app password>

Usage (from repo root)::

    python manual_testing/verify_deep_links.py                # dry run, preview only
    python manual_testing/verify_deep_links.py --post         # actually post to Bluesky
    python manual_testing/verify_deep_links.py --max-pulls 10 # search harder
"""

import argparse
import os
import random
import sys
from pathlib import Path

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


def collect_pets(max_pulls: int, limit: int):
    """Pull the API up to max_pulls times; stop once we have a supported pet.

    Returns (all_pets, supported_pets) deduped by pet_id.
    """
    all_by_id: dict[str, object] = {}
    supported: dict[str, object] = {}
    for i in range(max_pulls):
        source = SourceRescueGroups(limit=limit)
        try:
            pets = list(source.fetch_pets())
        except Exception as exc:
            print(f"  pull {i + 1}: FAILED {type(exc).__name__}: {exc}", file=sys.stderr)
            continue
        new_supported = 0
        for pet in pets:
            if not pet.pet_id:
                continue
            all_by_id[pet.pet_id] = pet
            if is_supported_org(pet.adoption_url):
                if pet.pet_id not in supported:
                    new_supported += 1
                supported[pet.pet_id] = pet
        print(f"  pull {i + 1}: {len(pets)} pets, "
              f"+{new_supported} from supported shelters "
              f"(total supported so far: {len(supported)})")
        if supported:
            break
    return list(all_by_id.values()), list(supported.values())


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
    # Flag MSPCA specifically since we're still figuring out its link format.
    mspca = [p for p in all_pets if "mspca.org" in (_domain_of(p.adoption_url) or "")]
    if mspca:
        print("\nMSPCA pets seen (for link-format investigation):")
        for p in mspca:
            print(f"    pet_id={p.pet_id}  url={p.adoption_url}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--post", action="store_true",
                        help="Actually publish to Bluesky (default is a dry-run preview).")
    parser.add_argument("--max-pulls", type=int, default=8,
                        help="Max random API pulls while searching (default 8).")
    parser.add_argument("--limit", type=int, default=100,
                        help="Pets per pull (default 100).")
    args = parser.parse_args()

    load_dotenv()
    if not os.environ.get("CUTEPETSBOSTON_RESCUEGROUPS_API_KEY"):
        print("CUTEPETSBOSTON_RESCUEGROUPS_API_KEY not set (put it in .env).", file=sys.stderr)
        return 1

    print(f"Searching for a supported-shelter pet (up to {args.max_pulls} pulls)...")
    all_pets, supported = collect_pets(args.max_pulls, args.limit)
    print(f"\nDone: {len(all_pets)} distinct pets seen, "
          f"{len(supported)} from supported shelters.")
    print_org_tally(all_pets)

    if not supported:
        print("\nNo pet from a supported shelter showed up. Try a higher --max-pulls, "
              "or these shelters may have no current listings.")
        return 2

    pet = random.choice(supported)
    poster = PosterBluesky()
    post = poster.format_post(pet)

    print("\n" + "=" * 70)
    print(f"SELECTED: {pet.name}  [pet_id={pet.pet_id}]  ({pet.location})")
    print(f"DEEP LINK (open to verify it lands on the pet):\n  {pet.adoption_url}")
    print("-" * 70)
    print("Bluesky post text:\n")
    print(post.text)
    print(f"\nTags: {post.tags}")
    print(f"Image: {post.image_url}")
    print("=" * 70)

    if not args.post:
        print("\nDRY RUN — nothing posted. Re-run with --post to publish to Bluesky.")
        return 0

    if not poster._is_available:
        print("\nBluesky credentials not set (BLUESKY_HANDLE / BLUESKY_PASSWORD).", file=sys.stderr)
        return 1
    print("\nPublishing to Bluesky...")
    result = poster.publish(post)
    if result.success:
        print(f"POSTED. post_url={result.post_url}")
        return 0
    print(f"POST FAILED: {result.error_message}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
