import unittest
from unittest import mock

from adoption_sources.rescue_groups import SourceRescueGroups


def _make_animal(adoption_url=None, **extra_attrs):
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
        "relationships": {"orgs": {"data": [{"type": "orgs", "id": "org1"}]}},
    }


def _make_org(adoption_url=None, url=None):
    attrs = {"city": "Boston", "state": "MA"}
    if adoption_url is not None:
        attrs["adoptionUrl"] = adoption_url
    if url is not None:
        attrs["url"] = url
    return attrs


class AdoptionUrlTests(unittest.TestCase):
    def setUp(self):
        self.source = SourceRescueGroups(api_key="dummy")

    def test_uses_pet_adoption_url_when_present(self):
        animal = _make_animal(adoption_url="https://pet.example.com/buddy")
        orgs = {"org1": _make_org(adoption_url="https://org.example.com", url="https://org.example.com/fallback")}

        pet = self.source._parse_animal(animal, orgs)

        self.assertEqual(pet.adoption_url, "https://pet.example.com/buddy")

    def test_falls_back_to_org_adoption_url_when_pet_has_none(self):
        animal = _make_animal()
        orgs = {"org1": _make_org(adoption_url="https://org.example.com/adopt", url="https://org.example.com")}

        pet = self.source._parse_animal(animal, orgs)

        self.assertEqual(pet.adoption_url, "https://org.example.com/adopt")

    def test_falls_back_to_org_url_when_neither_pet_nor_org_has_adoption_url(self):
        animal = _make_animal()
        orgs = {"org1": _make_org(url="https://org.example.com")}

        pet = self.source._parse_animal(animal, orgs)

        self.assertEqual(pet.adoption_url, "https://org.example.com")


class ArlLivenessTests(unittest.TestCase):
    """24PetConnect deep links are used only when confirmed live."""

    def setUp(self):
        self.source = SourceRescueGroups(api_key="dummy")

    def _arl_animal(self):
        animal = _make_animal(rescueId="A300563")
        animal["id"] = "22628355"
        return animal

    @mock.patch("adoption_sources.rescue_groups._deep_link_is_live", return_value=True)
    def test_live_deep_link_is_kept(self, _live):
        orgs = {"org1": _make_org(url="https://www.arlboston.org/")}
        pet = self.source._parse_animal(self._arl_animal(), orgs)
        self.assertEqual(
            pet.adoption_url,
            "https://24petconnect.com/ARLBostonAdoptablePets/Details/BSTN/A300563",
        )

    @mock.patch("adoption_sources.rescue_groups._deep_link_is_live", return_value=False)
    def test_dead_deep_link_falls_back_to_org_page(self, _live):
        orgs = {"org1": _make_org(url="https://www.arlboston.org/")}
        pet = self.source._parse_animal(self._arl_animal(), orgs)
        self.assertEqual(pet.adoption_url, "https://www.arlboston.org/")

    @mock.patch("adoption_sources.rescue_groups._deep_link_is_live", return_value=False)
    def test_non_petconnect_deep_link_skips_liveness_check(self, live):
        # Sterling's toolkit link is not liveness-checked, so it's kept even
        # though the (patched) checker would report it dead.
        animal = _make_animal()
        animal["id"] = "22506352"
        orgs = {"org1": _make_org(url="https://sterlingshelter.org/")}
        pet = self.source._parse_animal(animal, orgs)
        self.assertIn("sterlingshelter.org/pet-finder/", pet.adoption_url)
        live.assert_not_called()


class PlaceholderNameTests(unittest.TestCase):
    def setUp(self):
        self.source = SourceRescueGroups(api_key="dummy")

    def test_more_dogs_soon_is_placeholder(self):
        self.assertTrue(self.source._is_placeholder_name("More Dogs Soon!"))
        self.assertTrue(self.source._is_placeholder_name("MORE DOGS SOON!"))

    def test_real_pet_name_is_not_placeholder(self):
        self.assertFalse(self.source._is_placeholder_name("Pippin"))
        self.assertFalse(self.source._is_placeholder_name("Buddy"))


if __name__ == "__main__":
    unittest.main()
