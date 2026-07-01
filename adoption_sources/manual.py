"""Manual PetSource returning a fixed set of adoptable pets."""

from __future__ import annotations

import json
from typing import Iterable, Sequence

from abstractions import AdoptablePet, PetSource
from config import CITY_NAME, CITY_STATE
import logging
import pprint

logger = logging.getLogger(__name__)

_data_path = __file__.replace(".py", ".json")
with open(_data_path) as _f:
    MANUAL_SOURCE_DATA: tuple[dict, ...] = tuple(json.loads(_f.read()))
    log_data = pprint.pformat(MANUAL_SOURCE_DATA)
    logger.debug('API Response: %s', log_data)


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
        for animal in self._animals:
            yield self._build_pet(animal)

    def _build_pet(self, animal: dict) -> AdoptablePet:
        attrs = animal.get("attributes", {})
        animal_id = animal.get("id", "")
        return AdoptablePet(
            name=attrs.get("name", "Unknown"),
            species=self.species,
            breed=self._determine_breed(attrs),
            location=self.location_label,
            description=(attrs.get("descriptionText") or "").strip(),
            adoption_url=self._adoption_url(attrs.get("slug")),
            image_url=attrs.get("pictureThumbnailUrl"),
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
