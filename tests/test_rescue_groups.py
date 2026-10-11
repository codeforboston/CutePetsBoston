import json
import unittest
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from adoption_sources.rescue_groups import (
    SourceRescueGroups,
    _build_species_filters,
)
from social_posters.mastodon import PosterMastodon


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
            self.assertTrue(pet.image_urls)
            self.assertIn("width=800", pet.image_urls[0])


# Transcribed from the API log screenshots attached to #177. descriptionText
# loses the separators that are still present in descriptionHtml.
REX_HTML = (
    "<p>Adoptable in: MA, RI, NH, CT, and VT<br /><br />"
    "Good with dogs: Yes, with proper intros<br />"
    "Good with cats: Unknown, likely yes<br />"
    "Good with kids: Unknown, likely yes<br />"
    "Crate trained: Working on it<br />"
    "House Trained: Working on it<br /><br />"
    "Rex is a handsome, affectionate boy who&rsquo;s ready to "
    "wiggle his way into your heart!<br /><br />"
    "Please apply at <a href='http://www.lasthopek9.org/'>"
    "www.lasthopek9.org</a>.</p>"
)
REX_TEXT = (
    "Adoptable in: MA, RI, NH, CT, and VTGood with dogs: Yes, with proper intros"
    "Good with cats: Unknown, likely yesGood with kids: Unknown, likely yes"
    "Crate trained: Working on itHouse Trained: Working on it"
    "Rex is a handsome, affectionate boy who&rsquo;s ready to "
    "wiggle his way into your heart!Please apply at www.lasthopek9.org."
)
EXPECTED_REX = (
    "Adoptable in: MA, RI, NH, CT, and VT\n\n"
    "Good with dogs: Yes, with proper intros\n"
    "Good with cats: Unknown, likely yes\n"
    "Good with kids: Unknown, likely yes\n"
    "Crate trained: Working on it\n"
    "House Trained: Working on it\n\n"
    "Rex is a handsome, affectionate boy who’s ready to "
    "wiggle his way into your heart!\n\n"
    "Please apply at www.lasthopek9.org."
)


def parse_description(**attributes):
    pet = SourceRescueGroups(api_key="dummy")._parse_animal(
        _make_animal(**attributes), {"org1": _make_org()}, _make_species_by_id()
    )
    assert pet is not None
    return pet.description


@pytest.mark.parametrize("markup", [None, "", "  ", "<p>&nbsp;</p>", "<img src='tracker'>"])
def test_falls_back_to_text_when_html_has_no_readable_content(markup):
    assert parse_description(descriptionHtml=markup, descriptionText="Meet Rex &amp; friends.") == "Meet Rex & friends."


def test_html_only_description_is_used():
    assert parse_description(descriptionHtml="<p>Meet Rex!</p><p>He loves walks.</p>") == "Meet Rex!\n\nHe loves walks."


def test_preserves_inline_words_and_separates_blocks_and_lists():
    markup = (
        "<div>Meet <strong>Rex</strong>! He is house<span>trained</span>.</div>"
        "<ul><li>Good with dogs</li><li>Crate trained</li></ul>"
        "<p>Apply&nbsp;today: <a href='https://example.org/adopt'>adopt Rex</a>.</p>"
        "<script>tracking code</script><style>hidden styling</style><!-- comment -->"
    )
    assert parse_description(descriptionHtml=markup) == (
        "Meet Rex! He is housetrained.\n\nGood with dogs\nCrate trained\n\n"
        "Apply today: adopt Rex."
    )


def test_source_formatting_whitespace_does_not_create_extra_paragraphs():
    markup = "\n  <p>Meet\n    <b>Rex</b>!</p>\n  <p>He loves walks.</p>\n"
    assert parse_description(descriptionHtml=markup) == "Meet Rex!\n\nHe loves walks."


def test_html_entities_are_displayed_as_text_not_parsed_as_tags():
    assert parse_description(descriptionHtml="<p>Rex &lt;3 walks &amp; treats.</p>") == "Rex <3 walks & treats."


def test_rex_spacing_reaches_mastodon_status_requests():
    response = Mock()
    response.json.return_value = {
        "data": [_make_animal(name="Rex", descriptionHtml=REX_HTML, descriptionText=REX_TEXT)],
        "included": [
            {"type": "orgs", "id": "org1", "attributes": _make_org()},
            {"type": "species", "id": "8", "attributes": {"plural": "dogs"}},
        ],
    }
    with patch("adoption_sources.rescue_groups._session_with_retries") as session:
        session.return_value.post.return_value = response
        (pet,) = SourceRescueGroups(api_key="dummy").fetch_pets()

    assert pet.description == EXPECTED_REX
    poster = PosterMastodon()
    post = poster.format_post(pet)
    assert EXPECTED_REX in post.text
    root, replies = poster._format_caption_thread(post)
    client = Mock()
    client.status_post.side_effect = [{"id": str(i)} for i in range(1 + len(replies))]
    list(poster._post_thread(client, root, replies, ["media-id"]))
    payloads = [call.args[0] for call in client.status_post.call_args_list]
    sent = "\n".join(payloads)
    assert "VT\n\nGood with dogs:" in sent
    assert "intros\nGood with cats:" in sent
    assert "House Trained: Working on it\n\nRex is" in sent
    assert "VTGood" not in sent
    assert "itHouse" not in sent
    assert "itRex" not in sent
    assert "<br" not in sent
    assert "<p>" not in sent

if __name__ == "__main__":
    unittest.main()
