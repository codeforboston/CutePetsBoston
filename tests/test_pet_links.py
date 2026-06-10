import unittest

from adoption_sources.pet_links import _domain_of, reconstruct_adoption_url
from adoption_sources.rescue_groups import SourceRescueGroups


class DomainOfTests(unittest.TestCase):
    def test_strips_www_and_scheme(self):
        self.assertEqual(_domain_of("https://www.sterlingshelter.org/"), "sterlingshelter.org")

    def test_keeps_subdomain_other_than_www(self):
        self.assertEqual(_domain_of("https://adopt.sterlingshelter.org/x"), "adopt.sterlingshelter.org")

    def test_drops_port(self):
        self.assertEqual(_domain_of("https://sterlingshelter.org:8443/pet"), "sterlingshelter.org")

    def test_none_and_empty(self):
        self.assertIsNone(_domain_of(None))
        self.assertIsNone(_domain_of(""))
        self.assertIsNone(_domain_of("not a url"))


class ReconstructAdoptionUrlTests(unittest.TestCase):
    def test_sterling_deep_link(self):
        self.assertEqual(
            reconstruct_adoption_url(["https://sterlingshelter.org/"], "22506352"),
            "https://sterlingshelter.org/pet-finder/#action_0=pet&animalID_0=22506352&petIndex_0=-1",
        )

    def test_smalldog_deep_link(self):
        self.assertEqual(
            reconstruct_adoption_url(["https://www.smalldogrescuene.org/"], "999"),
            "https://www.smalldogrescuene.org/adoptable-dogs/#action_0=pet&animalID_0=999&petIndex_0=-1",
        )

    def test_matches_via_subdomain(self):
        self.assertEqual(
            reconstruct_adoption_url(["https://adopt.sterlingshelter.org/foo"], "1"),
            "https://sterlingshelter.org/pet-finder/#action_0=pet&animalID_0=1&petIndex_0=-1",
        )

    def test_first_matching_candidate_wins(self):
        # Unknown domain is skipped; the known one is used.
        self.assertEqual(
            reconstruct_adoption_url(
                [None, "https://rescuegroups.org/foo", "https://sterlingshelter.org/"], "42"
            ),
            "https://sterlingshelter.org/pet-finder/#action_0=pet&animalID_0=42&petIndex_0=-1",
        )

    def test_mspca_uses_lowercased_rescue_id(self):
        self.assertEqual(
            reconstruct_adoption_url(["http://www.mspca.org/boston"], "22301016", rescue_id="A467410"),
            "https://www.mspca.org/pets/a467410/",
        )

    def test_mspca_without_rescue_id_returns_none(self):
        # MSPCA's template needs rescue_id, not the RescueGroups pet_id.
        self.assertIsNone(reconstruct_adoption_url(["http://www.mspca.org/boston"], "22301016"))

    def test_unknown_domain_returns_none(self):
        self.assertIsNone(reconstruct_adoption_url(["https://www.example.org/adoption-search/"], "5"))

    def test_missing_pet_id_returns_none(self):
        self.assertIsNone(reconstruct_adoption_url(["https://sterlingshelter.org/"], None))
        self.assertIsNone(reconstruct_adoption_url(["https://sterlingshelter.org/"], ""))


class ParseAnimalIntegrationTests(unittest.TestCase):
    """The deep link should be applied end-to-end in SourceRescueGroups."""

    def setUp(self):
        self.source = SourceRescueGroups(api_key="dummy")

    def _animal(self):
        return {
            "type": "animals",
            "id": "22506352",
            "attributes": {"name": "Ketchup", "breedString": "Lab Mix"},
            "relationships": {"orgs": {"data": [{"type": "orgs", "id": "org1"}]}},
        }

    def test_toolkit_org_gets_deep_link(self):
        orgs = {"org1": {"city": "Sterling", "state": "MA", "url": "https://sterlingshelter.org/"}}
        pet = self.source._parse_animal(self._animal(), orgs)
        self.assertEqual(
            pet.adoption_url,
            "https://sterlingshelter.org/pet-finder/#action_0=pet&animalID_0=22506352&petIndex_0=-1",
        )

    def test_non_toolkit_org_keeps_landing_url(self):
        orgs = {"org1": {"city": "Boston", "state": "MA", "url": "https://www.mspca.org/"}}
        pet = self.source._parse_animal(self._animal(), orgs)
        self.assertEqual(pet.adoption_url, "https://www.mspca.org/")


if __name__ == "__main__":
    unittest.main()
