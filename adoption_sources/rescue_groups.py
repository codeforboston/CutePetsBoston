"""
RescueGroups.org API implementation of the PetSource interface.

API Documentation: https://api.rescuegroups.org/v5/public/docs
"""

import html
import logging
import pprint
import os
import re
from collections.abc import Sequence
from typing import Iterator

import requests
from ftfy import fix_and_explain
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from abstractions import AdoptablePet, PetSource
from adoption_sources.pet_links import reconstruct_adoption_url
from config import CITY_NAME, CITY_STATE, PET_SPECIES, POSTAL_CODE, RESCUEGROUPS_LIMIT

logger = logging.getLogger(__name__)

# Some rescues publish entries like "More Dogs Soon!" to point users at their
# website; those should never be posted. Add new names here as we encounter them.
PLACEHOLDER_NAMES: tuple[str, ...] = ("more dogs soon!", "more cats soon!")

# Values used by the rest of the application.
SPECIES_SINGULAR = {"dogs": "dog", "cats": "cat"}

# RescueGroups filter criteria are case-sensitive and use title-cased values
# in the API's documented multi-species search example.
FILTER_SPECIES_SINGULAR = {"dogs": "Dog", "cats": "Cat"}

# The RescueGroups API occasionally times out or returns a transient 5xx. A
# single hiccup shouldn't fail the whole run, so retry a few times with
# exponential backoff (0s, 2s, 4s, 8s between attempts).
RETRY_TOTAL = 4
RETRY_BACKOFF_FACTOR = 1

def _session_with_retries() -> requests.Session:
    """Build a requests Session that retries transient errors with backoff."""
    retry = Retry(
        total=RETRY_TOTAL,
        backoff_factor=RETRY_BACKOFF_FACTOR,
        status_forcelist=(429, 500, 502, 503, 504),
        # We only POST, so POST must be opted in (it isn't retried by default).
        allowed_methods=frozenset({"POST"}),
        raise_on_status=False,
    )
    session = requests.Session()
    session.mount("https://", HTTPAdapter(max_retries=retry))
    return session


def _build_species_filters(species: Sequence[str]) -> tuple[list[dict], str]:
    """Build search filters and filterProcessing for an OR species search.

    Filters use the title-cased ``species.singular`` criteria from the
    documented RescueGroups multi-species search example. #124 was silently
    rejected by the live API (zero results), so any change here must be
    re-verified against the real API (tests/test_rescue_groups_live.py).
    """
    if not species:
        raise ValueError("At least one species is required")
    filters = [
        {
            "fieldName": "species.singular",
            "operation": "equals",
            "criteria": FILTER_SPECIES_SINGULAR[plural],
        }
        for plural in species
    ]
    filter_processing = " OR ".join(str(index) for index in range(1, len(filters) + 1))
    return filters, filter_processing


class SourceRescueGroups(PetSource):
    """
    Fetches adoptable pets from RescueGroups.org API.

    Requires CUTEPETSBOSTON_RESCUEGROUPS_API_KEY environment variable or api_key constructor arg.
    """

    BASE_URL = "https://api.rescuegroups.org/v5/public/animals/search"

    def __init__(
        self,
        api_key: str | None = None,
        postal_code: str = POSTAL_CODE,
        radius_miles: int = 50,
        species: Sequence[str] | None = None,
        limit: int = RESCUEGROUPS_LIMIT,
        location_label: str = f"{CITY_NAME}, {CITY_STATE}",
    ):
        self._api_key = api_key or os.environ.get("CUTEPETSBOSTON_RESCUEGROUPS_API_KEY")
        self.postal_code = postal_code
        self.radius_miles = radius_miles
        self.species = tuple(species if species is not None else PET_SPECIES)
        self.limit = limit
        self.location_label = location_label

    @property
    def source_name(self) -> str:
        return f"RescueGroups ({', '.join(self.species)})"

    def fetch_pets(self) -> Iterator[AdoptablePet]:
        """
        Fetch available pets from RescueGroups.org.

        Yields:
            AdoptablePet objects for each available pet.

        Raises:
            ValueError: If API key is not configured.
            requests.HTTPError: If the API request fails.
        """
        if not self._api_key:
            raise ValueError(
                "RescueGroups API key not configured. "
                "Set CUTEPETSBOSTON_RESCUEGROUPS_API_KEY environment variable."
            )

        url = (
            f"{self.BASE_URL}/available/haspic"
            f"?include=orgs,breeds,locations,species"
            f"&sort=random"
            f"&limit={self.limit}"
        )
        headers = {
            "Content-Type": "application/vnd.api+json",
            "Authorization": self._api_key,
        }
        species_filters, filter_processing = _build_species_filters(self.species)
        # filterRadius is the documented POST-body key for radius searches.
        # See _build_species_filters for why body-shape changes need a live
        # API check.
        payload = {
            "data": {
                "filters": species_filters,
                "filterProcessing": filter_processing,
                "filterRadius": {
                    "miles": self.radius_miles,
                    "postalcode": self.postal_code,
                },
            }
        }

        logger.info(
            f"Fetching {', '.join(self.species)} from RescueGroups "
            f"within {self.radius_miles} miles of {self.postal_code}"
        )

        session = _session_with_retries()
        response = session.post(url, json=payload, headers=headers, timeout=30)
        response.raise_for_status()

        body = response.json()
        data = body.get("data", [])
        logger.info(f"Received {len(data)} pets from RescueGroups")

        data_log = pprint.pformat(data)
        logger.debug('API Response: \n%s', data_log)


        orgs_by_id = {
            item["id"]: item.get("attributes", {})
            for item in body.get("included", [])
            if item.get("type") == "orgs"
        }
        species_by_id = {
            item["id"]: item.get("attributes", {})
            for item in body.get("included", [])
            if item.get("type") == "species"
        }

        for animal in data:
            pet = self._parse_animal(animal, orgs_by_id, species_by_id)
            if not pet:
                continue
            if self._is_placeholder_name(pet.name):
                logger.info(f"Skipping placeholder record: {pet.name!r}")
                continue
            yield pet

    def _parse_animal(
        self,
        animal: dict,
        orgs_by_id: dict,
        species_by_id: dict,
    ) -> AdoptablePet | None:
        """Parse a single animal record from the API response."""
        try:
            attrs = animal.get("attributes", {})
            animal_id = animal.get("id", "")

            # Extract and clean the name
            name = self._clean_name(attrs.get("name", "Unknown"), animal_id=animal_id)

            # Determine species from the included species relationship
            species_id = (
                animal.get("relationships", {})
                .get("species", {})
                .get("data", [{}])[0]
                .get("id")
            )
            if not species_id:
                logger.warning(f"Skipping animal {animal_id} with no species relationship")
                return None
            plural = species_by_id.get(species_id, {}).get("plural")
            normalized_plural = plural.lower() if isinstance(plural, str) else ""
            if normalized_plural not in self.species:
                logger.info(f"Skipping animal {animal_id} with unconfigured species: {plural!r}")
                return None
            species = SPECIES_SINGULAR[normalized_plural]

            # Get breed info
            breed = self._repair_mojibake(
                attrs.get("breedString", attrs.get("breedPrimary", "Mixed")),
                "breed",
                animal_id,
            )

            # Clean up description (use text version, not HTML)
            description = self._clean_description(
                attrs.get("descriptionText", ""), animal_id=animal_id
            )

            # Get adoption_url
            org_id = (
                animal.get("relationships", {})
                .get("orgs", {})
                .get("data", [{}])[0]
                .get("id")
            )
            org_attrs = orgs_by_id.get(org_id, {}) if org_id else {}
            url_candidates = (
                attrs.get("adoptionUrl"),
                org_attrs.get("adoptionUrl"),
                org_attrs.get("url"),
            )
            adoption_url = next(
                (u for u in url_candidates
                 if u and u.strip().rstrip("/") not in ("http:", "https:", "http://", "https://")),
                None
            )

            # Shelter's own animal id (e.g. MSPCA's "A468573"); some orgs' deep
            # links are keyed on this rather than the RescueGroups id.
            rescue_id = attrs.get("rescueId")

            # For shelters we have a template for, rebuild a deep link to this
            # specific pet; otherwise keep the org landing page from above.
            adoption_url = (
                reconstruct_adoption_url(url_candidates, animal_id, rescue_id)
                or adoption_url
            )

            # Get best available image
            image_url = self._get_image_url(attrs)

            # Location of the adoption org
            location = self._repair_mojibake(
                f"{org_attrs.get('city')}, {org_attrs.get('state')}",
                "location",
                org_id or "unknown",
                "organization",
            )


            return AdoptablePet(
                name=name,
                species=species,
                breed=breed,
                location=location,
                description=description,
                adoption_url=adoption_url,
                image_url=image_url,
                age_string=attrs.get("ageString"),
                sex=attrs.get("sex"),
                size_group=attrs.get("sizeGroup"),
                pet_id=animal_id,
                rescue_id=rescue_id,
            )
        except Exception as e:
            logger.warning(f"Failed to parse animal {animal.get('id', 'unknown')}: {e}")
            return None

    def _is_placeholder_name(self, name: str) -> bool:
        return name.lower() in PLACEHOLDER_NAMES

    def _repair_mojibake(
        self,
        text: str,
        field: str,
        entity_id: str,
        entity_type: str = "animal",
    ) -> str:
        """Apply ftfy's complete set of repairs to RescueGroups display text.

        This deliberately uses ftfy's default configuration, including its
        mixed/lossy encoding recovery and general Unicode cleanup. The complete
        ``ExplainedText`` result is logged whenever ftfy changes a value.
        """
        if not text:
            return text

        result = fix_and_explain(text)
        repaired = result.text
        if repaired != text:
            logger.info(
                "Fixed RescueGroups %s for %s %s: ftfy_result=%r",
                field,
                entity_type,
                entity_id,
                result,
            )
            return repaired
        return text

    def _clean_name(self, name: str, animal_id: str = "unknown") -> str:
        """
        Clean up pet name by removing promotional text.

        Examples:
            "Doli ***Home for the Holidays 1/2 price!" -> "Doli"
            "Kathy" -> "Kathy"
        """
        # Fix before splitting. ftfy weighs the whole string when a sequence
        # is ambiguous (``Ã…`` is both mojibaked ``Å`` and plausible real text),
        # so discarding the promotional suffix first can lose the only evidence
        # that tips an accented name toward being repaired.
        name = self._repair_mojibake(name, "name", animal_id)

        # Remove common promotional suffixes
        # Split on common delimiters and take the first part
        cleaned = re.split(r"\s*[\*\-\|]+\s*", name)[0]
        return cleaned.strip()

    def _clean_description(
        self, description: str, animal_id: str = "unknown"
    ) -> str:
        """Clean up description text."""
        if not description:
            return ""

        # Decode HTML entities first, so mojibake that arrived entity-encoded
        # (&#226;&euro;&trade;) is repairable too.
        text = html.unescape(description)
        # A description may combine paragraphs copied from systems with
        # different encodings. Treat natural line boundaries independently so
        # ftfy can assess each paragraph on its own.
        text = "".join(
            self._repair_mojibake(line, "description", animal_id)
            for line in text.splitlines(keepends=True)
        )

        # Remove &nbsp; and normalize whitespace
        text = text.replace("&nbsp;", " ")
        text = re.sub(r"\s+", " ", text)

        # Remove promotional headers
        text = re.sub(
            r"\*\*Home for the Holidays.*?\*\*", "", text, flags=re.IGNORECASE
        )

        return text

    def _get_image_url(self, attrs: dict) -> str | None:
        """Get the best available image URL."""
        thumbnail = attrs.get("pictureThumbnailUrl")
        if thumbnail:
            # Request a larger image instead of the 100px thumbnail
            return re.sub(r"\?width=\d+", "?width=800", thumbnail)
        return None
