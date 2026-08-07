import json
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from adoption_sources.rescue_groups import (
    SourceRescueGroups,
    _build_species_filters,
)


def _make_animal(adoption_url=None, species_id="8", **extra_attrs):
    attrs = {
        "name": "Buddy",
        "breedString": "Lab Mix",
        "pictureThumbnailUrl": "https://example.com/buddy.jpg",
        **extra_attrs,
    }
    if adoption_url is not None:
        attrs["adoptionUrl"] = adoption_url
    return {
        "type": "animals",
        "id": "12345",
        "attributes": attrs,
        "relationships": {
            "orgs": {"data": [{"type": "orgs", "id": "org1"}]},
            "species": {"data": [{"type": "species", "id": species_id}]},
        },
    }


def _make_org(adoption_url=None, url=None):
    attrs = {"city": "Boston", "state": "MA"}
    if adoption_url is not None:
        attrs["adoptionUrl"] = adoption_url
    if url is not None:
        attrs["url"] = url
    return attrs


def _make_species_by_id(plural="dogs", species_id="8"):
    return {species_id: {"plural": plural}}


class BuildSpeciesFiltersTests(unittest.TestCase):
    def test_two_species_uses_or_filter_processing(self):
        filters, filter_processing = _build_species_filters(("dogs", "cats"))

        self.assertEqual(
            filters,
            [
                {"fieldName": "species.singular", "operation": "equals", "criteria": "Dog"},
                {"fieldName": "species.singular", "operation": "equals", "criteria": "Cat"},
            ],
        )
        self.assertEqual(filter_processing, "1 OR 2")

    def test_single_species(self):
        filters, filter_processing = _build_species_filters(("dogs",))

        self.assertEqual(len(filters), 1)
        self.assertEqual(filter_processing, "1")

    def test_no_species_raises(self):
        with self.assertRaises(ValueError):
            _build_species_filters(())


class AdoptionUrlTests(unittest.TestCase):
    def setUp(self):
        self.source = SourceRescueGroups(api_key="dummy")
        self.species_by_id = _make_species_by_id()

    def test_uses_pet_adoption_url_when_present(self):
        animal = _make_animal(adoption_url="https://pet.example.com/buddy")
        orgs = {"org1": _make_org(adoption_url="https://org.example.com", url="https://org.example.com/fallback")}

        pet = self.source._parse_animal(animal, orgs, self.species_by_id)

        self.assertEqual(pet.adoption_url, "https://pet.example.com/buddy")

    def test_falls_back_to_org_adoption_url_when_pet_has_none(self):
        animal = _make_animal()
        orgs = {"org1": _make_org(adoption_url="https://org.example.com/adopt", url="https://org.example.com")}

        pet = self.source._parse_animal(animal, orgs, self.species_by_id)

        self.assertEqual(pet.adoption_url, "https://org.example.com/adopt")

    def test_falls_back_to_org_url_when_neither_pet_nor_org_has_adoption_url(self):
        animal = _make_animal()
        orgs = {"org1": _make_org(url="https://org.example.com")}

        pet = self.source._parse_animal(animal, orgs, self.species_by_id)

        self.assertEqual(pet.adoption_url, "https://org.example.com")


class SpeciesParsingTests(unittest.TestCase):
    def setUp(self):
        self.source = SourceRescueGroups(api_key="dummy")
        self.orgs = {"org1": _make_org(url="https://org.example.com")}

    def test_dog_species_from_included(self):
        animal = _make_animal(species_id="8")
        species_by_id = _make_species_by_id(plural="Dogs", species_id="8")

        pet = self.source._parse_animal(animal, self.orgs, species_by_id)

        self.assertEqual(pet.species, "dog")

    def test_cat_species_from_included(self):
        animal = _make_animal(species_id="3")
        species_by_id = _make_species_by_id(plural="Cats", species_id="3")

        pet = self.source._parse_animal(animal, self.orgs, species_by_id)

        self.assertEqual(pet.species, "cat")

    def test_skips_unconfigured_species(self):
        animal = _make_animal(species_id="99")
        species_by_id = _make_species_by_id(plural="rabbits", species_id="99")

        pet = self.source._parse_animal(animal, self.orgs, species_by_id)

        self.assertIsNone(pet)

    def test_skips_animal_without_species_relationship(self):
        animal = _make_animal()
        del animal["relationships"]["species"]

        pet = self.source._parse_animal(animal, self.orgs, _make_species_by_id())

        self.assertIsNone(pet)


class PlaceholderNameTests(unittest.TestCase):
    def setUp(self):
        self.source = SourceRescueGroups(api_key="dummy")

    def test_more_dogs_soon_is_placeholder(self):
        self.assertTrue(self.source._is_placeholder_name("More Dogs Soon!"))
        self.assertTrue(self.source._is_placeholder_name("MORE DOGS SOON!"))

    def test_more_cats_soon_is_placeholder(self):
        self.assertTrue(self.source._is_placeholder_name("More Cats Soon!"))
        self.assertTrue(self.source._is_placeholder_name("MORE CATS SOON!"))

    def test_real_pet_name_is_not_placeholder(self):
        self.assertFalse(self.source._is_placeholder_name("Pippin"))
        self.assertFalse(self.source._is_placeholder_name("Buddy"))


class DescriptionCleaningTests(unittest.TestCase):
    def setUp(self):
        self.source = SourceRescueGroups(api_key="dummy")

    def test_repairs_latin_1_mojibake_observed_in_api_response(self):
        description = "Adoption hours: 1:00PM â\x80\x93 6:00PM"
        animal = _make_animal(descriptionText=description)

        with self.assertLogs(
            "adoption_sources.rescue_groups", level="INFO"
        ) as captured:
            pet = self.source._parse_animal(
                animal,
                {"org1": _make_org(url="https://example.com/adopt")},
                _make_species_by_id(),
            )

        self.assertEqual(pet.description, "Adoption hours: 1:00PM – 6:00PM")
        self.assertEqual(
            captured.output,
            [
                "INFO:adoption_sources.rescue_groups:Repaired mojibake in "
                "RescueGroups description for animal 12345 using latin-1"
            ],
        )

    def test_repairs_windows_1252_mojibake_after_html_unescape(self):
        description = "I&#226;&euro;&trade;m ready for a home."

        cleaned = self.source._clean_description(description)

        self.assertEqual(cleaned, "I’m ready for a home.")

    def test_preserves_valid_unicode(self):
        descriptions = (
            "José loves café visits – and naps.",
            "A happy dog 😊",
            "猫はとても元気です。",
        )

        for description in descriptions:
            with self.subTest(description=description):
                self.assertEqual(
                    self.source._clean_description(description), description
                )

    def test_repairs_mojibake_beside_unrelated_unicode(self):
        description = "José says hello 😊 Iâ€™m friendly."

        cleaned = self.source._clean_description(description)

        self.assertEqual(cleaned, "José says hello 😊 I’m friendly.")


class FetchPetsRequestTests(unittest.TestCase):
    @patch("adoption_sources.rescue_groups._session_with_retries")
    def test_posts_single_multi_species_request(self, mock_session_factory):
        mock_session = MagicMock()
        mock_session_factory.return_value = mock_session
        mock_response = MagicMock()
        mock_response.json.return_value = {"data": [], "included": []}
        mock_session.post.return_value = mock_response

        source = SourceRescueGroups(api_key="dummy")
        pets = list(source.fetch_pets())

        self.assertEqual(pets, [])
        mock_session.post.assert_called_once()
        url = mock_session.post.call_args.args[0]
        payload = mock_session.post.call_args.kwargs["json"]

        self.assertIn("/available/haspic", url)
        self.assertNotIn("/dogs/", url)
        self.assertIn("include=orgs,breeds,locations,species", url)
        self.assertEqual(
            payload["data"]["filters"],
            [
                {"fieldName": "species.singular", "operation": "equals", "criteria": "Dog"},
                {"fieldName": "species.singular", "operation": "equals", "criteria": "Cat"},
            ],
        )
        self.assertEqual(payload["data"]["filterProcessing"], "1 OR 2")
        self.assertEqual(
            payload["data"]["filterRadius"],
            {"miles": 50, "postalcode": "02108"},
        )
        self.assertNotIn("geodistance", payload["data"])

    def test_missing_api_key_raises(self):
        source = SourceRescueGroups(api_key=None)
        source._api_key = None  # ignore any ambient env var

        with self.assertRaises(ValueError):
            list(source.fetch_pets())


class RealCaptureParsingTests(unittest.TestCase):
    """Parse the real API capture end-to-end, as a guard against drift
    between our parsing and what the live API actually returns."""

    def test_real_capture_parses(self):
        fixture = Path(__file__).parent / "fixtures" / "sample_data.json"
        with open(fixture) as f:
            raw_animals = json.load(f)

        source = SourceRescueGroups(api_key="dummy")
        species_by_id = {"8": {"plural": "dogs"}}

        for raw in raw_animals:
            pet = source._parse_animal(raw, {}, species_by_id)
            self.assertIsNotNone(pet, f"failed to parse animal {raw['id']}")
            self.assertEqual(pet.species, "dog")
            self.assertTrue(pet.name)
            self.assertTrue(pet.breed)
            self.assertTrue(pet.image_url)
            self.assertIn("width=800", pet.image_url)


if __name__ == "__main__":
    unittest.main()
