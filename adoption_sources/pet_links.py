"""Reconstruct deep links to an individual pet's adoption page.

The RescueGroups API gives us an org's *landing* page (e.g.
``https://sterlingshelter.org/``), not a link to the specific animal. Some orgs
embed the RescueGroups "web toolkit" (``toolkit.rescuegroups.org/j/3/.../toolkit.js``),
which renders a single animal when the page URL carries a hash fragment of the
form::

    <pet-finder page>#action_0=pet&animalID_0=<animal id>

``animalID_0`` is the RescueGroups animal id -- the exact value the API returns
as ``animal["id"]`` and we store as ``AdoptablePet.pet_id`` -- so we can rebuild
the deep link without scraping. (``petIndex_0`` only drives next/prev nav within
a result list and is not needed to load a specific animal.)

We only reconstruct for orgs we have verified use the toolkit; every other org
falls back to whatever URL the API provided.
"""

from typing import Iterable
from urllib.parse import urlparse

# Domain -> (template, id_key). Each org's pet page is reachable from one of the
# ids we get from the API:
#   * "pet_id"          -- the RescueGroups numeric animal id (toolkit shelters).
#   * "rescue_id"       -- the shelter's own animal id (RescueGroups "rescueId",
#                          e.g. "A300071"), used as-is (ARL Boston's 24PetConnect urls).
#   * "rescue_id_lower" -- the same shelter animal id, lowercased
#                          (MSPCA's /pets/a######/ urls).
# The template uses a single ``{id}`` placeholder filled with that id.
#
# Sterling, SmallDog & Pug Rescue embed the RescueGroups toolkit v3; the trailing
# ``petIndex_0=-1`` is the toolkit's "standalone pet, not part of a browsed list"
# sentinel -- without it the widget can show the full list instead of the animal.
#
# ARL Boston's site (arlboston.org) hands pet detail pages off to 24PetConnect, so
# the template's output domain differs from the matched org domain -- that's fine,
# _template_for_domain matches on the org URL, the template just points elsewhere.
PET_FINDER_TEMPLATES: dict[str, tuple[str, str]] = {
    "sterlingshelter.org": (
        "https://sterlingshelter.org/pet-finder/#action_0=pet&animalID_0={id}&petIndex_0=-1",
        "pet_id",
    ),
    "smalldogrescuene.org": (
        "https://www.smalldogrescuene.org/adoptable-dogs/#action_0=pet&animalID_0={id}&petIndex_0=-1",
        "pet_id",
    ),
    "pugrescueofnewengland.org": (
        "https://pugrescueofnewengland.org/available-pugs/#action_0=pet&animalID_0={id}&petIndex_0=-1",
        "pet_id",
    ),
    "paw-affectionrescue.org": (
        "https://www.paw-affectionrescue.org/animals/detail?AnimalID={id}",
        "pet_id",
    ),
    "mspca.org": (
        "https://www.mspca.org/pets/{id}/",
        "rescue_id_lower",
    ),
    "arlboston.org": (
        "https://24petconnect.com/ARLBostonAdoptablePets/Details/BSTN/{id}",
        "rescue_id",
    ),
}


def _domain_of(url: str | None) -> str | None:
    """Return the lowercased host of ``url`` without a leading ``www.``."""
    if not url:
        return None
    netloc = urlparse(url.strip()).netloc.lower()
    if not netloc:
        return None
    # Drop any user:pass@ and :port, then a leading www.
    netloc = netloc.rsplit("@", 1)[-1].split(":", 1)[0]
    return netloc[4:] if netloc.startswith("www.") else netloc


def _template_for_domain(domain: str | None) -> tuple[str, str] | None:
    if not domain:
        return None
    # Exact match or any subdomain of a known org (e.g. adopt.sterlingshelter.org).
    for known, entry in PET_FINDER_TEMPLATES.items():
        if domain == known or domain.endswith("." + known):
            return entry
    return None


def is_supported_org(url: str | None) -> bool:
    """True if ``url``'s domain is a shelter we have a deep-link template for."""
    return _template_for_domain(_domain_of(url)) is not None


def reconstruct_adoption_url(
    candidate_urls: Iterable[str | None],
    pet_id: str | None,
    rescue_id: str | None = None,
) -> str | None:
    """Build a deep link to a specific pet, or ``None`` if we can't.

    Args:
        candidate_urls: URLs from the API that might reveal the org's domain
            (adoption URL, org adoption URL, org website, ...). Checked in order;
            the first whose domain matches a known org wins.
        pet_id: The RescueGroups numeric animal id (``AdoptablePet.pet_id``).
        rescue_id: The shelter's own animal id (``AdoptablePet.rescue_id`` /
            RescueGroups "rescueId"), used by orgs like MSPCA.

    Returns:
        A reconstructed deep link, or ``None`` when no candidate domain is known
        or the id that org's template needs is missing.
    """
    ids = {
        "pet_id": pet_id or None,
        "rescue_id": rescue_id or None,
        "rescue_id_lower": rescue_id.lower() if rescue_id else None,
    }
    for url in candidate_urls:
        entry = _template_for_domain(_domain_of(url))
        if not entry:
            continue
        template, id_key = entry
        id_value = ids.get(id_key)
        if id_value:
            return template.format(id=id_value)
        # Domain matched but we lack the id it needs -> fall back (try next url).
    return None
