"""
RescueGroups.org API implementation of the PetSource interface.

API Documentation: https://api.rescuegroups.org/v5/public/docs
"""

import html
import logging
import os
import re
from typing import Iterator
import json

import requests

from abstractions import AdoptablePet, PetSource

logger = logging.getLogger(__name__)


class SourceRescueGroups(PetSource):
    """
    Fetches adoptable pets from RescueGroups.org API.

    Requires CUTEPETSBOSTON_RESCUEGROUPS_API_KEY environment variable or api_key constructor arg.
    """

    BASE_URL = "https://api.rescuegroups.org/v5/public/animals/search"

    def __init__(
        self,
        api_key: str | None = None,
        postal_code: str = "02108",  # Boston
        radius_miles: int = 50,
        species: str = "dogs",  # "dogs" or "cats"
        limit: int = 25,
        location_label: str = "Boston, MA",  # For display purposes
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
            f"{self.BASE_URL}/available/{self.species}/haspic"
            f"?include=breeds,locations"
            f"&sort=random"
            f"&limit={self.limit}"
        )
        headers = {
            "Content-Type": "application/vnd.api+json",
            "Authorization": self._api_key,
        }
        payload = {
            "data": {
                "filterRadius": {
                    "miles": self.radius_miles,
                    "postalcode": self.postal_code,
                }
            }
        }


        logger.info(
            f"Fetching {self.species} from RescueGroups within {self.radius_miles} miles of {self.postal_code}"
        )

        response = requests.post(url, json=payload, headers=headers, timeout=30)
        response.raise_for_status()

        data = response.json().get("data", [])
        print(data)
        logger.info(f"Received {len(data)} pets from RescueGroups")

        for animal in data:
            pet = self._parse_animal(animal)
            if pet:
                yield pet

    def _parse_animal(self, animal: dict) -> AdoptablePet | None:
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

            # Build adoption URL from slug
            slug = attrs.get("slug", "")
            adoption_url = f"https://www.rescuegroups.org/pet/{slug}" if slug else None

            # Get best available image
            image_url = self._get_image_url(attrs)

            return AdoptablePet(
                name=name,
                species=species,
                breed=breed,
                location=self.location_label,
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
