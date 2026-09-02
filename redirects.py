"""Slug minting and the append-only redirect mapping (RFC 0001).

The mapping lives as ``redirects.json`` on the ``gh-pages`` branch. Git
history is the durable, append-only store; nothing here ever overwrites or
deletes an existing slug, so a link posted to social media never dies.

Git operations (fetch/commit/push of the mapping) live in the workflows;
this module only handles the pure JSON/slug logic so it stays testable.
"""

import hashlib
import json
import logging
import os
import re
from pathlib import Path
from urllib.parse import urlparse

from config import SITE_URL

logger = logging.getLogger(__name__)

DEFAULT_REDIRECTS_PATH = "redirects.json"
REDIRECT_PATH = "/r/"

# Slugs must match what docs/r/index.html accepts: [A-Za-z0-9_-]+
_SLUG_FORBIDDEN = re.compile(r"[^A-Za-z0-9_-]")

_TRUTHY = {"1", "true", "yes", "on"}


def enabled():
    """Whether redirect minting is on. Only prod sets REDIRECTS_ENABLED."""
    return os.environ.get("REDIRECTS_ENABLED", "").strip().lower() in _TRUTHY


def mint_slug(pet_id):
    """Derive a stable, URL-safe slug from a RescueGroups pet id (RFC D6).

    Sanitising alone is not injective -- "pet/42 x" and "pet-42-x" both collapse
    to "pet-42-x", which would silently point one pet's post at another pet's
    listing. When sanitising actually changes the id, append a short digest of
    the raw id so distinct ids keep distinct slugs. Ids that are already
    URL-safe (every RescueGroups id today) come back unchanged, so no link
    already in the wild is affected.
    """
    if pet_id is None or str(pet_id).strip() == "":
        raise ValueError("cannot mint a redirect slug without a pet_id")
    raw = str(pet_id).strip()
    slug = _SLUG_FORBIDDEN.sub("-", raw)
    if slug != raw:
        # hashlib, not the builtin hash(): that one is salted per process, so
        # it would mint a different slug for the same pet on every run.
        slug = f"{slug}-{hashlib.sha256(raw.encode('utf-8')).hexdigest()[:6]}"
    return slug


def redirect_url_for(slug):
    """The public URL posted to social media for a slug."""
    return f"{SITE_URL}{REDIRECT_PATH}?id={slug}"


def load_redirects(path=None):
    """Load the slug -> adoptionLink mapping.

    A missing file is an empty mapping (first run); a corrupt file raises so
    the run fails loudly instead of silently rebuilding a broken store. Callers
    that must not be blocked by a broken store catch that ValueError -- see
    mint_for_pet.
    """
    mapping_path = Path(path or DEFAULT_REDIRECTS_PATH)
    if not mapping_path.exists() or mapping_path.stat().st_size == 0:
        return {}
    try:
        data = json.loads(mapping_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise ValueError(f"{mapping_path} is not valid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError(f"{mapping_path} must contain a JSON object of slug -> url")
    return data


def save_redirects(mapping, path=None):
    """Write the mapping atomically (tmp file + replace), mirroring database.json."""
    mapping_path = Path(path or DEFAULT_REDIRECTS_PATH)
    temporary_path = mapping_path.with_name(f"{mapping_path.name}.tmp")
    with temporary_path.open("w", encoding="utf-8") as mapping_file:
        json.dump(mapping, mapping_file, indent=2, sort_keys=True)
        mapping_file.write("\n")
    temporary_path.replace(mapping_path)


def is_safe_target(url):
    """Whether url is safe to send a visitor to.

    docs/r/index.html navigates with location.replace(), which would execute a
    "javascript:" URL in our own origin. RescueGroups hands us adoption URLs
    verbatim and the mapping is append-only, so a bad target would be permanent
    -- reject anything that is not plain http(s).
    """
    try:
        return urlparse(str(url)).scheme in ("http", "https")
    except (TypeError, ValueError):
        return False


def register_redirect(mapping, slug, adoption_url):
    """Append-only add of slug -> adoption_url. Never overwrite or delete.

    If the slug already exists (pet relisted after the 12-week repost window),
    the existing target is kept so the old link keeps working.

    Returns (mapping, changed) where changed indicates whether the caller
    needs to persist and deploy a new mapping.
    """
    if not is_safe_target(adoption_url):
        logger.error(
            "refusing to map slug %r to unsafe target %r; only http(s) is allowed",
            slug,
            adoption_url,
        )
        return mapping, False

    existing = mapping.get(slug)
    if existing is not None:
        if existing == adoption_url:
            return mapping, False
        logger.warning(
            "slug %r already maps to %r; keeping existing target (append-only)",
            slug,
            existing,
        )
        return mapping, False
    mapping[slug] = adoption_url
    return mapping, True


def mint_for_pet(pet, redirects_path=None):
    """Mint (or reuse) the slug for pet and persist the mapping.

    Returns the redirect URL to post, or None when no redirect can be minted
    (missing pet_id, an unsafe adoption URL, or an unreadable mapping) -- in
    every one of those cases the raw adoption URL is used, so a data quirk or a
    damaged store never blocks a post.
    """
    if not getattr(pet, "pet_id", None):
        logger.warning(
            "Pet %s has no pet_id; posting the raw adoption URL without a redirect",
            getattr(pet, "name", "unknown"),
        )
        return None

    if not is_safe_target(pet.adoption_url):
        logger.error(
            "Pet %s has a non-http(s) adoption URL %r; posting it without a redirect",
            getattr(pet, "name", "unknown"),
            pet.adoption_url,
        )
        return None

    mapping_path = redirects_path or DEFAULT_REDIRECTS_PATH
    slug = mint_slug(pet.pet_id)
    try:
        mapping = load_redirects(mapping_path)
    except ValueError as exc:
        # Posting pets is the job; a broken redirect store must not stop it.
        # Returning before save_redirects leaves the damaged file untouched
        # for a human to look at, and the raw adoption URL gets posted.
        logger.error("Cannot mint a redirect, mapping is unreadable: %s", exc)
        return None
    mapping, changed = register_redirect(mapping, slug, pet.adoption_url)
    if changed:
        save_redirects(mapping, mapping_path)
    return redirect_url_for(slug)
