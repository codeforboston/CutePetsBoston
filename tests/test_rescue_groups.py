import unittest
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
                {"fieldName": "species.plural", "operation": "equal", "criteria": "dogs"},
                {"fieldName": "species.plural", "operation": "equal", "criteria": "cats"},
            ],
        )
        self.assertEqual(filter_processing, "1 OR 2")

    def test_single_species(self):
        filters, filter_processing = _build_species_filters(("dogs",))

        self.assertEqual(len(filters), 1)
        self.assertEqual(filter_processing, "1")


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
        species_by_id = _make_species_by_id(plural="dogs", species_id="8")

        pet = self.source._parse_animal(animal, self.orgs, species_by_id)

        self.assertEqual(pet.species, "dog")

    def test_cat_species_from_included(self):
        animal = _make_animal(species_id="3")
        species_by_id = _make_species_by_id(plural="cats", species_id="3")

        pet = self.source._parse_animal(animal, self.orgs, species_by_id)

        self.assertEqual(pet.species, "cat")

    def test_skips_unconfigured_species(self):
        animal = _make_animal(species_id="99")
        species_by_id = _make_species_by_id(plural="rabbits", species_id="99")

        pet = self.source._parse_animal(animal, self.orgs, species_by_id)

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


class FetchPetsRequestTests(unittest.TestCase):
    @patch("adoption_sources.rescue_groups._session_with_retries")
    def test_posts_single_multi_species_request(self, mock_session_factory):
        mock_session = MagicMock()
        mock_session_factory.return_value = mock_session
        mock_response = MagicMock()
        mock_response.json.return_value = {"data": [], "included": []}
        mock_session.post.return_value = mock_response

        source = SourceRescueGroups(api_key="dummy")
        list(source.fetch_pets())

        mock_session.post.assert_called_once()
        url = mock_session.post.call_args.args[0]
        payload = mock_session.post.call_args.kwargs["json"]

        self.assertIn("/available/haspic", url)
        self.assertNotIn("/dogs/", url)
        self.assertIn("include=orgs,breeds,locations,species", url)
        self.assertEqual(payload["data"]["filterProcessing"], "1 OR 2")
        self.assertEqual(len(payload["data"]["filters"]), 2)


if __name__ == "__main__":
    unittest.main()
