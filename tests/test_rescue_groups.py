import json
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from requests import Response

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


def _mojibake(text: str, encoding: str = "cp1252") -> str:
    """Corrupt ``text`` the way a mis-decoding upstream system does.

    UTF-8 bytes read back one at a time as a single-byte codepage. ``cp1252``
    leaves five bytes undefined (0x81, 0x8D, 0x8F, 0x90, 0x9D) and real systems
    fall through to Latin-1 for those, which is why live descriptions mix tidy
    ``â€™`` runs with raw C1 control characters. Pass ``encoding="latin-1"``
    for the pure Latin-1 flavour we captured in the GOOBER post.
    """
    decoded = []
    for byte in text.encode("utf-8"):
        chunk = bytes([byte])
        try:
            decoded.append(chunk.decode(encoding))
        except UnicodeDecodeError:
            decoded.append(chunk.decode("latin-1"))
    return "".join(decoded)


# A description in the shape shelters actually write, holding one example of
# every mojibake class we have seen or can expect: smart punctuation, Latin-1
# accents, symbols, and astral-plane emoji. Written as lines because
# ``_clean_description`` collapses whitespace, so the newlines become spaces.
LEGIT_DESCRIPTION_LINES = (
    "Meet Goober! 🐶 He’s a 2-year-old Lab mix and he weighs 52 lbs.",
    "Adoption hours are 1:00PM – 6:00PM, Tuesday–Sunday; the fee is $150.",
    "His foster, José, calls him “the best boy” — crate-trained, "
    "house-trained… and 100% food-motivated.",
    "• Neutered: yes • Good with kids: yes • Cats: a slow introduction, "
    "and keep the house at 70°F or cooler, please 😊",
    "Questions? Email adopt@example.org, or apply at "
    "https://example.com/adopt/jos%C3%A9 — se habla español "
    "(Doña Müller answers on weekends).",
    "Sponsored by PetSmart™ & the Ångström Family Fund.",
)
LEGIT_DESCRIPTION = "\n".join(LEGIT_DESCRIPTION_LINES)
EXPECTED_DESCRIPTION = " ".join(LEGIT_DESCRIPTION_LINES)


class DescriptionMojibakeRepairTests(unittest.TestCase):
    def setUp(self):
        self.source = SourceRescueGroups(api_key="dummy")

    def test_repairs_a_realistic_description_mangled_as_windows_1252(self):
        self.assertEqual(
            self.source._clean_description(_mojibake(LEGIT_DESCRIPTION, "cp1252")),
            EXPECTED_DESCRIPTION,
        )

    def test_repairs_a_realistic_description_mangled_as_latin_1(self):
        self.assertEqual(
            self.source._clean_description(_mojibake(LEGIT_DESCRIPTION, "latin-1")),
            EXPECTED_DESCRIPTION,
        )

    def test_repairs_a_corrupted_paragraph_beside_clean_text(self):
        """Shelters paste a mangled paragraph into otherwise clean text."""
        clean = "Meet Goober! 🐶 His foster José says he’s “the best boy”."
        corrupted = _mojibake(
            "Adoption hours: 1:00PM – 6:00PM. Doña Müller answers. 😊"
        )

        cleaned = self.source._clean_description(f"{clean}\n{corrupted}")

        self.assertEqual(
            cleaned,
            f"{clean} Adoption hours: 1:00PM – 6:00PM. Doña Müller answers. 😊",
        )

    def test_repairs_non_breaking_space_before_whitespace_is_collapsed(self):
        """``Â\\xa0`` must be repaired before whitespace normalization runs."""
        self.assertEqual(
            self.source._clean_description(_mojibake("Goober weighs 52 lbs.")),
            "Goober weighs 52 lbs.",
        )

    def test_repairs_mojibake_that_arrives_as_html_entities(self):
        self.assertEqual(
            self.source._clean_description("I&#226;&euro;&trade;m ready for a home."),
            "I’m ready for a home.",
        )

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
        self.assertEqual(len(captured.records), 1)
        self.assertEqual(
            captured.records[0].args,
            (
                "description",
                "animal",
                "12345",
                "encode(latin-1) -> decode(utf-8)",
            ),
        )

    def test_declines_repair_that_requires_reconstructing_a_missing_byte(self):
        description = "voilÃ le travail"

        with self.assertNoLogs("adoption_sources.rescue_groups", level="INFO"):
            repaired = self.source._clean_description(
                description, animal_id="multi-step"
            )

        self.assertEqual(repaired, description)

    def test_declines_mixed_encoding_within_one_paragraph(self):
        description = (
            "Clean José 🐶. "
            + _mojibake("Adoption hours: 1:00PM – 6:00PM. Doña answers.")
        )

        with self.assertNoLogs("adoption_sources.rescue_groups", level="INFO"):
            cleaned = self.source._clean_description(description)

        self.assertEqual(cleaned, description)

    @patch("adoption_sources.rescue_groups.fix_encoding_and_explain")
    def test_rejects_any_repair_plan_with_a_non_round_trip_step(self, mock_fix):
        original = "ambiguous input"
        mock_fix.return_value = SimpleNamespace(
            text="guessed output",
            explanation=[
                SimpleNamespace(action="encode", parameter="latin-1"),
                SimpleNamespace(action="transcode", parameter="restore_byte_a0"),
                SimpleNamespace(action="decode", parameter="utf-8"),
            ],
        )

        repaired = self.source._repair_mojibake(
            original, "description", "test-animal"
        )

        self.assertEqual(repaired, original)


class DennisMojibakeMastodonRegressionTests(unittest.TestCase):
    """Regression coverage for RescueGroups animal 22658169 (DENNIS).

    The record was captured from the live RescueGroups API on 2026-08-10.
    It verifies that mojibaked punctuation is repaired before text reaches
    Mastodon's ``status_post`` boundary.
    """

    def test_real_dennis_mojibake_is_repaired_before_mastodon_post(self):
        raw_animal = {
            "type": "animals",
            "id": "22658169",
            "attributes": {
                "ageGroup": "Senior",
                "ageString": "7 Years 3 Months",
                "birthDate": "2019-04-06T00:00:00Z",
                "breedPrimary": "Domestic Short Hair",
                "breedPrimaryId": 35,
                "breedString": "Domestic Short Hair (medium coat)",
                "coatLength": "Medium",
                "name": "DENNIS",
                "rescueId": "A299137",
                "sex": "Male",
                "sizeGroup": "Medium",
                "pictureThumbnailUrl": (
                    "https://cdn.rescuegroups.org/1975/pictures/"
                    "animals/22658/22658169/103556832.jpg?width=100"
                ),
                "descriptionText": (
                    "MEET DENNIS!- I am in a foster home, please call the "
                    "Boston shelter to learn more or come meet me in the "
                    "shelter on Sundays during adoption hours!"
                    "Dennis is the sweetest guy looking for his new home! "
                    "Heâ\x80\x99s diabetic, so he needs a little extra daily "
                    "care, but he will give you more than enough love to make "
                    "it worth it! Whether itâ\x80\x99s zooming around with "
                    "his favorite toys, watching his favorite cat tv, lovingly "
                    "showing you his belly, or snuggling with you, Dennis is "
                    "sure to make you smile. He is a silly and quirky guy in "
                    "the best way, and he will keep you laughing with his "
                    "antics. Heâ\x80\x99ll let you know heâ\x80\x99s coming "
                    "to sit on your lap with an activation trill, and "
                    "heâ\x80\x99d be glad to lifeguard you while "
                    "youâ\x80\x99re showering to protect you from the scary "
                    "water. Heâ\x80\x99s also good at setting boundaries and "
                    "will let you know if needs a break from pets. If "
                    "youâ\x80\x99re looking for a sweet and funny guy to "
                    "brighten your home, Dennis may be the cat for you! "
                    "Dennis is diabetic and his diabetes is being managed "
                    "with twice daily insulin. To offset the cost of medical "
                    "care, his adoption fee has waived. Dennis is currently "
                    "up to date on all vaccinations, has been spayed/neutered, "
                    "microchipped and seen by our vet team."
                    "We welcome adopters from NH, RI, CT, and NY however, we "
                    "are unable to facilitate same day adoptions due to state "
                    "regulated paperwork requirements."
                    "For more information on this or any other animal currently "
                    "residing at the Animal Rescue League of Boston please "
                    "visit us during our adoption center hours: "
                    "Wednesdays-Sundays from 1:00PM â\x80\x93 6:00PM, "
                    "Tuesdays by appointment only from "
                    "1:00PM â\x80\x93 6:00PM, closed Mondays & Holidays."
                    "For information about our adoption process click here"
                ),
            },
            "relationships": {
                "breeds": {"data": [{"id": "35", "type": "breeds"}]},
                "locations": {
                    "data": [{"id": "1000001975", "type": "locations"}]
                },
                "orgs": {"data": [{"id": "1975", "type": "orgs"}]},
                "species": {"data": [{"id": "3", "type": "species"}]},
            },
        }
        orgs_by_id = {
            "1975": {
                "city": "Boston",
                "state": "MA",
                "url": "http://www.arlboston.org",
            }
        }
        species_by_id = {"3": {"plural": "Cats"}}

        raw_description = raw_animal["attributes"]["descriptionText"]
        self.assertIn("Heâ\x80\x99s diabetic", raw_description)
        self.assertIn("1:00PM â\x80\x93 6:00PM", raw_description)

        source = SourceRescueGroups(api_key="dummy")
        with self.assertLogs(
            "adoption_sources.rescue_groups", level="INFO"
        ) as captured_logs:
            pet = source._parse_animal(raw_animal, orgs_by_id, species_by_id)

        self.assertIsNotNone(pet)
        assert pet is not None
        self.assertIn("He’s diabetic", pet.description)
        self.assertIn("Whether it’s zooming", pet.description)
        self.assertIn("He’ll let you know", pet.description)
        self.assertIn("you’re showering", pet.description)
        self.assertIn("1:00PM – 6:00PM", pet.description)
        self.assertNotIn("â\x80\x99", pet.description)
        self.assertNotIn("â\x80\x93", pet.description)
        self.assertIn(
            "Repaired mojibake in RescueGroups description for animal 22658169",
            "\n".join(captured_logs.output),
        )
        self.assertEqual(pet.pet_id, "22658169")
        self.assertEqual(pet.name, "DENNIS")
        self.assertEqual(pet.species, "cat")
        self.assertEqual(pet.breed, "Domestic Short Hair (medium coat)")
        self.assertEqual(pet.location, "Boston, MA")

        poster = PosterMastodon.__new__(PosterMastodon)
        post = poster.format_post(pet)
        self.assertIn("He’s diabetic", post.text)
        self.assertIn("Whether it’s zooming", post.text)
        self.assertIn("1:00PM – 6:00PM", post.text)
        self.assertNotIn("â\x80\x99", post.text)
        self.assertNotIn("â\x80\x93", post.text)

        session = MagicMock()

        def fake_status_post(text, **kwargs):
            call_number = session.status_post.call_count
            return {
                "id": f"status-{call_number}",
                "url": f"https://mastodon.example/@test/status-{call_number}",
            }

        session.status_post.side_effect = fake_status_post
        poster._session = session
        poster._is_available = True
        poster._auth_error = None
        poster._upload_media = MagicMock(return_value="media-1")

        result = poster.publish(post)

        self.assertTrue(result.success)
        self.assertEqual(result.post_id, "status-1")
        poster._upload_media.assert_called_once_with(session, post)
        self.assertGreaterEqual(session.status_post.call_count, 1)

        mastodon_payloads = [
            call.args[0] for call in session.status_post.call_args_list
        ]
        all_text_sent_to_mastodon = "\n".join(mastodon_payloads)
        self.assertIn("’", all_text_sent_to_mastodon)
        self.assertIn("–", all_text_sent_to_mastodon)
        self.assertNotIn("â\x80\x99", all_text_sent_to_mastodon)
        self.assertNotIn("â\x80\x93", all_text_sent_to_mastodon)
        self.assertNotIn("\x80", all_text_sent_to_mastodon)
        self.assertNotIn("\x99", all_text_sent_to_mastodon)
        self.assertNotIn("\x93", all_text_sent_to_mastodon)

        root_call = session.status_post.call_args_list[0]
        self.assertEqual(root_call.kwargs["media_ids"], ["media-1"])
        for reply_call in session.status_post.call_args_list[1:]:
            self.assertEqual(reply_call.kwargs["in_reply_to_id"], "status-1")


class DescriptionPreservationTests(unittest.TestCase):
    """The repair leaves text alone when there is nothing to repair.

    These are the tests that fail if ``fix_encoding`` ever starts over-reaching:
    they all pass against the pre-repair code, so only a regression breaks them.
    """

    # The shapes most likely to be mistaken for mojibake: real Latin-1 letters
    # (â is what mojibake starts with), percent-encoded URLs (a repair would
    # break the link), and the cp1252 symbols that mojibake decodes *into*.
    CLEAN_DESCRIPTIONS = {
        "real a-circumflex": "Château, Ângela, and Râ are real words.",
        "correct smart punctuation": "He’s “the best boy” — really… 100% good.",
        "percent-encoded url": "Apply at https://example.com/adopt/jos%C3%A9?ref=a%E2%80%93b",
        "trademarks and degrees": "PetSmart™ · Petco® · 70°F · ©2026 Example Rescue",
        "non-latin scripts": "猫はとても元気です。 강아지 귀여워요! Кот очень милый.",
    }

    def setUp(self):
        self.source = SourceRescueGroups(api_key="dummy")

    def test_leaves_clean_descriptions_byte_for_byte_identical(self):
        for label, description in self.CLEAN_DESCRIPTIONS.items():
            with self.subTest(label):
                self.assertEqual(
                    self.source._clean_description(description), description
                )

    def test_leaves_the_full_realistic_description_untouched_and_unlogged(self):
        with self.assertNoLogs("adoption_sources.rescue_groups", level="INFO"):
            cleaned = self.source._clean_description(LEGIT_DESCRIPTION)

        self.assertEqual(cleaned, EXPECTED_DESCRIPTION)

    def test_leaves_ambiguous_capital_a_tilde_untouched(self):
        description = "Letters like Ã and Ê are rare."

        with self.assertNoLogs("adoption_sources.rescue_groups", level="INFO"):
            cleaned = self.source._clean_description(description)

        self.assertEqual(cleaned, description)

    def test_leaves_ambiguous_capital_a_circumflex_and_space_untouched(self):
        description = "Â is a letter in Romanian and Vietnamese."

        with self.assertNoLogs("adoption_sources.rescue_groups", level="INFO"):
            cleaned = self.source._clean_description(description)

        self.assertEqual(cleaned, description)


class PetFieldMojibakeRepairTests(unittest.TestCase):
    """A mojibaked name is the most visible failure of the lot — it lands in
    the post title — so name, breed, and location are covered alongside the
    description they were originally left out of."""

    # Shelters really do use accented names, breeds, and cities.
    LEGIT_NAME = "Renée ***Home for the Holidays 1/2 price!"
    EXPECTED_NAME = "Renée"
    LEGIT_BREED = "Bichon Frisé / Coton de Tuléar Mix"
    LEGIT_CITY = "Montréal"
    EXPECTED_LOCATION = "Montréal, QC"
    LEGIT_TEXT = "She’s a sweetheart – really."

    def setUp(self):
        self.source = SourceRescueGroups(api_key="dummy")

    def _animal(self, corrupt: bool):
        transform = _mojibake if corrupt else (lambda text: text)
        return _make_animal(
            name=transform(self.LEGIT_NAME),
            breedString=transform(self.LEGIT_BREED),
            descriptionText=transform(self.LEGIT_TEXT),
        )

    def _orgs(self, corrupt: bool):
        transform = _mojibake if corrupt else (lambda text: text)
        return {
            "org1": {
                "city": transform(self.LEGIT_CITY),
                "state": "QC",
                "url": "https://example.com/adopt",
            }
        }

    def _assert_all_fields_repaired(self, pet) -> None:
        self.assertEqual(pet.name, self.EXPECTED_NAME)
        self.assertEqual(pet.breed, self.LEGIT_BREED)
        self.assertEqual(pet.location, self.EXPECTED_LOCATION)
        self.assertEqual(pet.description, self.LEGIT_TEXT)

    def test_repairs_name_breed_and_location_through_fetch_pets(self):
        body = {
            "data": [self._animal(corrupt=True)],
            "included": [
                {
                    "type": "orgs",
                    "id": "org1",
                    "attributes": self._orgs(corrupt=True)["org1"],
                },
                {"type": "species", "id": "8", "attributes": {"plural": "dogs"}},
            ],
        }
        response = Response()
        response.status_code = 200
        response._content = json.dumps(body, ensure_ascii=False).encode("utf-8")
        mock_session = MagicMock()
        mock_session.post.return_value = response

        with patch(
            "adoption_sources.rescue_groups._session_with_retries",
            return_value=mock_session,
        ):
            pets = list(self.source.fetch_pets())

        self.assertEqual(len(pets), 1)
        self._assert_all_fields_repaired(pets[0])

    def test_logs_each_repaired_field_by_name(self):
        with self.assertLogs(
            "adoption_sources.rescue_groups", level="INFO"
        ) as captured:
            pet = self.source._parse_animal(
                self._animal(corrupt=True),
                self._orgs(corrupt=True),
                _make_species_by_id(),
            )

        self._assert_all_fields_repaired(pet)
        self.assertEqual(
            sorted(record.args[:3] for record in captured.records),
            sorted(
                [
                    (field, "animal", "12345")
                    for field in ("name", "breed", "description")
                ]
                + [("location", "organization", "org1")]
            ),
        )
        for record in captured.records:
            self.assertTrue(record.args[3])

    def test_leaves_clean_fields_untouched_and_unlogged(self):
        with self.assertNoLogs("adoption_sources.rescue_groups", level="INFO"):
            pet = self.source._parse_animal(
                self._animal(corrupt=False),
                self._orgs(corrupt=False),
                _make_species_by_id(),
            )

        self._assert_all_fields_repaired(pet)

    def test_repairs_name_before_stripping_the_promotional_suffix(self):
        """``Ã…`` is ambiguous on its own — ftfy only fixes it when the rest of
        the string corroborates. Splitting first throws that evidence away, so
        this name comes back as ``Ã…sa`` if the repair moves after the split.
        """
        self.assertEqual(
            self.source._clean_name(
                _mojibake("Åsa ***Ångström's littermate, adopt together!")
            ),
            "Åsa",
        )

    def test_repairs_name_and_breed_that_only_differ_in_smart_punctuation(self):
        self.assertEqual(
            self.source._clean_name(_mojibake("Lucky — the “office dog”")),
            "Lucky — the “office dog”",
        )
        self.assertEqual(
            self.source._repair_mojibake(
                _mojibake("Chihuahua – Short Coat"), "breed", "12345"
            ),
            "Chihuahua – Short Coat",
        )

    def test_empty_and_missing_values_pass_through(self):
        for value in ("", None):
            with self.subTest(value=value):
                self.assertEqual(
                    self.source._repair_mojibake(value, "breed", "12345"), value
                )

    def test_known_limitation_a_ring_needs_corroborating_mojibake(self):
        """Documented limitation, not desired behavior.

        ``Ã…`` is the cp1252 form of ``Å``, but it is also plausible real text,
        so ftfy leaves it alone unless the string carries other mojibake to
        corroborate it. Scandinavian names are where this bites.
        """
        self.assertEqual(
            self.source._clean_name(_mojibake("Åsa", "cp1252")), "Ã…sa"
        )
        # Latin-1 corruption of the same name has no such ambiguity.
        self.assertEqual(self.source._clean_name(_mojibake("Åsa", "latin-1")), "Åsa")
        # Neither does cp1252 corruption with a second mojibake sequence.
        self.assertEqual(
            self.source._clean_name(_mojibake("Åsa the Ångström hound")),
            "Åsa the Ångström hound",
        )


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
