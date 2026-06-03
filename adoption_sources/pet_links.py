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

# Domain -> deep-link template. Verified to embed the RescueGroups toolkit v3.
# The page path differs per org, so each domain carries its own full template.
# The trailing ``petIndex_0=-1`` is the toolkit's "standalone pet, not part of a
# browsed result list" sentinel. Without it the widget can fall back to showing
# the full list instead of the specific animal.
PET_FINDER_TEMPLATES: dict[str, str] = {
    "sterlingshelter.org": "https://sterlingshelter.org/pet-finder/#action_0=pet&animalID_0={pet_id}&petIndex_0=-1",
    "smalldogrescuene.org": "https://www.smalldogrescuene.org/adoptable-dogs/#action_0=pet&animalID_0={pet_id}&petIndex_0=-1",
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


def _template_for_domain(domain: str | None) -> str | None:
    if not domain:
        return None
    # Exact match or any subdomain of a known org (e.g. adopt.sterlingshelter.org).
    for known, template in PET_FINDER_TEMPLATES.items():
        if domain == known or domain.endswith("." + known):
            return template
    return None


def is_supported_org(url: str | None) -> bool:
    """True if ``url``'s domain is a shelter we can build deep links for."""
    return _template_for_domain(_domain_of(url)) is not None


def reconstruct_adoption_url(
    candidate_urls: Iterable[str | None], pet_id: str | None
) -> str | None:
    """Build a deep link to a specific pet, or ``None`` if we can't.

    Args:
        candidate_urls: URLs from the API that might reveal the org's domain
            (adoption URL, org adoption URL, org website, ...). Checked in order;
            the first whose domain matches a known toolkit org wins.
        pet_id: The RescueGroups animal id (``AdoptablePet.pet_id``).

    Returns:
        A reconstructed deep link, or ``None`` when no candidate domain is a
        known toolkit org or ``pet_id`` is missing.
    """
    if not pet_id:
        return None
    for url in candidate_urls:
        template = _template_for_domain(_domain_of(url))
        if template:
            return template.format(pet_id=pet_id)
    return None
