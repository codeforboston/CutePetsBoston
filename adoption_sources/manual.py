"""Manual PetSource returning a fixed set of adoptable pets."""

from __future__ import annotations

import json
import logging
import pprint
from typing import Iterable, Sequence

from abstractions import AdoptablePet, PetSource
from config import CITY_NAME, CITY_STATE

logger = logging.getLogger(__name__)


def get_animals_data(payload_dict: dict) -> Sequence[dict]:
    """Extract the list of animals from the API payload."""
    animals_data = payload_dict.get("data", [])
    return animals_data if isinstance(animals_data, list) else []


def parse_json_payload(payload: str) -> dict:
    """Parse the API payload and return a dictionary."""
    json_response = json.loads(payload)
    return json_response


def read_file(data_path: str) -> str:
    """Read the manual source data from the JSON file."""
    file_contents = None
    with open(data_path) as _f:
        file_contents = _f.read()
    return file_contents


_data_path = __file__.replace(".py", ".json")
MANUAL_SOURCE_DATA: tuple[dict, ...] = tuple(get_animals_data(parse_json_payload(read_file(_data_path))))


class SourceManual(PetSource):
    """Static PetSource useful for offline testing and demos."""

    def __init__(
        self,
        animals: Sequence[dict] | None = None,
        location_label: str = f"{CITY_NAME}, {CITY_STATE}",
        species: str = "dog",
    ) -> None:
        self._animals: Sequence[dict] = animals if animals is not None else MANUAL_SOURCE_DATA
        self.location_label = location_label
        self.species = species

    @property
    def source_name(self) -> str:
        return "Manual"

    def fetch_pets(self) -> Iterable[AdoptablePet]:
        log_data = pprint.pformat(MANUAL_SOURCE_DATA)
        logger.debug("API Response: \n%s", log_data)
        for animal in self._animals:
            yield self._build_pet(animal)

    def _build_pet(self, animal: dict) -> AdoptablePet:
        attrs = animal.get("attributes", {})
        animal_id = animal.get("id", "")
        # Clean up description (use text version, not HTML)
        description = self._clean_description(attrs.get("descriptionText", "")).strip()

        return AdoptablePet(
            name=attrs.get("name", "Unknown"),
            species=self.species,
            breed=self._determine_breed(attrs),
            location=self.location_label,
            description=description,
            adoption_url=self._adoption_url(attrs.get("adoptionUrl")),
            image_urls=[attrs["pictureThumbnailUrl"]] if attrs.get("pictureThumbnailUrl") else [],
            pet_id=animal_id,
        )

    @staticmethod
    def _determine_breed(attrs: dict) -> str:
        return attrs.get("breedString") or attrs.get("breedPrimary") or "Mixed"

    @staticmethod
    def _adoption_url(slug: str | None) -> str | None:
        if slug:
            return f"https://www.rescuegroups.org/pet/{slug}"
        return None


__all__ = ["SourceManual", "MANUAL_SOURCE_DATA"]
