"""
RescueGroups.org API implementation of the PetSource interface.

API Documentation: https://api.rescuegroups.org/v5/public/docs
"""

import html
import logging
import os
import re
import json
from typing import Iterator

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from abstractions import AdoptablePet, PetSource
from config import CITY_NAME, CITY_STATE, POSTAL_CODE

logger = logging.getLogger(__name__)

# Some rescues publish entries like "More Dogs Soon!" to point users at their
# website; those should never be posted. Add new names here as we encounter them.
PLACEHOLDER_NAMES: tuple[str, ...] = ("more dogs soon!",)

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


class SourceRescueGroups(PetSource):
    """
    Fetches adoptable pets from RescueGroups.org API.

    Requires CUTEPETSBOSTON_RESCUEGROUPS_API_KEY environment variable or api_key constructor arg.
    """

    BASE_URL = "https://api.rescuegroups.org/v5/public/orgs/8866"

    def __init__(
        self,
        api_key: str | None = None,
        postal_code: str = POSTAL_CODE,
        radius_miles: int = 50,
        species: str = "dogs",  # "dogs" or "cats"
        limit: int = 25,
        location_label: str = f"{CITY_NAME}, {CITY_STATE}",
    ):
        self._api_key = api_key or os.environ.get("CUTEPETSBOSTON_RESCUEGROUPS_API_KEY")
        self.postal_code = postal_code
        self.radius_miles = radius_miles
        self.species = species
        self.limit = limit
        self.location_label = location_label

    @property
    def source_name(self) -> str:
        return f"RescueGroups ({self.species})"

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
            f"{self.BASE_URL}"
            # f"?include=orgs,breeds,locations"
            # f"&sort=random"
            # f"&limit={self.limit}"
        )
        headers = {
            "Content-Type": "application/vnd.api+json",
            "Authorization": self._api_key,
        }
        payload = {
            # "data": {
            #     "filterRadius": {
            #         "miles": self.radius_miles,
            #         "postalcode": self.postal_code,
            #     }
            # }
        }

        logger.info(
            f"Fetching {self.species} from RescueGroups within {self.radius_miles} miles of {self.postal_code}"
        )

        session = _session_with_retries()
        response = session.post(url, json=payload, headers=headers, timeout=30)
        response.raise_for_status()

        body = response.json()
        data = body.get("data", [])
        print("Temporarily print response body")
        print(json.dumps(data, indent=4))
        logger.info(f"Received {len(data)} pets from RescueGroups")

        orgs_by_id = {
            item["id"]: item.get("attributes", {})
            for item in body.get("included", [])
            if item.get("type") == "orgs"
        }

        for animal in data:
            pet = self._parse_animal(animal, orgs_by_id)
            if not pet:
                continue
            if self._is_placeholder_name(pet.name):
                logger.info(f"Skipping placeholder record: {pet.name!r}")
                continue
            yield pet

    def _parse_animal(self, animal: dict, orgs_by_id: dict) -> AdoptablePet | None:
        """Parse a single animal record from the API response."""
        try:
            attrs = animal.get("attributes", {})
            animal_id = animal.get("id", "")

            # Extract and clean the name
            name = self._clean_name(attrs.get("name", "Unknown"))

            # Determine species from the endpoint we queried
            species = "dog" if self.species == "dogs" else "cat"

            # Get breed info
            breed = attrs.get("breedString", attrs.get("breedPrimary", "Mixed"))

            # Clean up description (use text version, not HTML)
            description = self._clean_description(attrs.get("descriptionText", ""))

            # Get adoption_url
            org_id = (
                animal.get("relationships", {})
                .get("orgs", {})
                .get("data", [{}])[0]
                .get("id")
            )
            org_attrs = orgs_by_id.get(org_id, {}) if org_id else {}
            adoption_url = next(
                (
                    u
                    for u in (
                        attrs.get("adoptionUrl"),
                        org_attrs.get("adoptionUrl"),
                        org_attrs.get("url"),
                    )
                    if u
                    and u.strip().rstrip("/")
                    not in ("http:", "https:", "http://", "https://")
                ),
                None,
            )

            # Get best available image
            image_url = self._get_image_url(attrs)

            # Location of the adoption org
            location = f"{org_attrs.get('city')}, {org_attrs.get('state')}"

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
            )
        except Exception as e:
            logger.warning(f"Failed to parse animal {animal.get('id', 'unknown')}: {e}")
            return None

    def _is_placeholder_name(self, name: str) -> bool:
        return name.lower() in PLACEHOLDER_NAMES

    def _clean_name(self, name: str) -> str:
        """
        Clean up pet name by removing promotional text.

        Examples:
            "Doli ***Home for the Holidays 1/2 price!" -> "Doli"
            "Kathy" -> "Kathy"
        """
        # Remove common promotional suffixes
        # Split on common delimiters and take the first part
        cleaned = re.split(r"\s*[\*\-\|]+\s*", name)[0]
        return cleaned.strip()

    def _clean_description(self, description: str) -> str:
        """Clean up description text."""
        if not description:
            return ""

        # Decode HTML entities
        text = html.unescape(description)

        # Remove &nbsp; and normalize whitespace
        text = text.replace("&nbsp;", " ")
        text = re.sub(r"\s+", " ", text)

        # Remove promotional headers
        text = re.sub(
            r"\*\*Home for the Holidays.*?\*\*", "", text, flags=re.IGNORECASE
        )

        # Trim to reasonable length for social posts
        text = text.strip()
        if len(text) > 500:
            text = text[:497] + "..."

        return text

    def _get_image_url(self, attrs: dict) -> str | None:
        """Get the best available image URL."""
        thumbnail = attrs.get("pictureThumbnailUrl")
        if thumbnail:
            # Request a larger image instead of the 100px thumbnail
            return re.sub(r"\?width=\d+", "?width=800", thumbnail)
        return None
