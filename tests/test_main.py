import json
import tempfile
import unittest
import uuid
from pathlib import Path
from unittest import mock

import main
from abstractions import AdoptablePet, Post, PostResult
from adoption_sources import SourceManual
from adoption_sources.rescue_groups import SourceRescueGroups
from config import SITE_URL
from main import create_posters, create_sources, run
from social_posters.debug import PosterDebug


class FakeSource:
    def __init__(self, pets):
        self.pets = pets
        self.fetch_called = False

    def fetch_pets(self):
        self.fetch_called = True
        return self.pets


class FakePoster:
    platform_name = "FakePoster"

    def __init__(self):
        self.format_called = False
        self.publish_called = False
        self.posts = []

    def format_post(self, pet):
        self.format_called = True
        return Post(text=f"Meet {pet.name}", image_url=pet.image_url)

    def publish(self, post):
        self.publish_called = True
        self.posts.append(post)
        return PostResult(success=True)


class TempRedirectsMixin:
    """Point REDIRECTS_PATH at a temp file so posting in tests never writes to
    the repo's docs/redirects.json."""

    def setUp(self):
        super().setUp()
        tmp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(tmp_dir.cleanup)
        self.redirects_path = Path(tmp_dir.name) / "redirects.json"
        patcher = mock.patch.object(main, "REDIRECTS_PATH", self.redirects_path)
        patcher.start()
        self.addCleanup(patcher.stop)


class RunFlowTests(TempRedirectsMixin, unittest.TestCase):
    def test_run_calls_source_and_posters(self):
        pet = AdoptablePet(
            name="Poppy",
            species="dog",
            breed="mutt",
            location="Boston, MA",
            image_url="https://example.com/poppy.jpg",
            adoption_url="https://example.com/adopt/poppy",
            pet_id=f"test-poppy-{uuid.uuid4()}",
        )
        source = FakeSource([pet])
        poster_one = FakePoster()
        poster_two = FakePoster()

        results = run([source], [poster_one, poster_two])

        self.assertTrue(source.fetch_called)
        self.assertTrue(poster_one.format_called)
        self.assertTrue(poster_one.publish_called)
        self.assertTrue(poster_two.format_called)
        self.assertTrue(poster_two.publish_called)
        self.assertEqual(len(results), 2)

    def test_run_with_mixed_species_pool(self):
        dog = AdoptablePet(
            name="Rex",
            species="dog",
            breed="mutt",
            location="Boston, MA",
            image_url="https://example.com/rex.jpg",
            adoption_url="https://example.com/adopt/rex",
            pet_id=f"test-dog-{uuid.uuid4()}",
        )
        cat = AdoptablePet(
            name="Luna",
            species="cat",
            breed="tabby",
            location="Boston, MA",
            image_url="https://example.com/luna.jpg",
            adoption_url="https://example.com/adopt/luna",
            pet_id=f"test-cat-{uuid.uuid4()}",
        )
        source = FakeSource([dog, cat])
        poster = FakePoster()

        results = run([source], [poster])

        self.assertTrue(poster.format_called)
        self.assertTrue(poster.publish_called)
        self.assertEqual(len(results), 1)


class RedirectLinkTests(TempRedirectsMixin, unittest.TestCase):
    def _pet(self, adoption_url="https://example.com/adopt/poppy"):
        return AdoptablePet(
            name="Poppy",
            species="dog",
            breed="mutt",
            location="Boston, MA",
            image_url="https://example.com/poppy.jpg",
            adoption_url=adoption_url,
            pet_id=f"test-poppy-{uuid.uuid4()}",
        )

    def test_pet_is_posted_with_redirect_url_not_adoption_url(self):
        pet = self._pet()

        run([FakeSource([pet])], [FakePoster()])

        self.assertEqual(pet.adoption_url, f"{SITE_URL}/r/?id={pet.pet_id}")

    def test_redirect_mapping_is_written(self):
        pet = self._pet()
        adoption_url = pet.adoption_url

        run([FakeSource([pet])], [FakePoster()])

        redirects = json.loads(self.redirects_path.read_text())
        self.assertEqual(redirects[pet.pet_id], adoption_url)

    def test_redirect_mapping_is_append_only(self):
        pet = self._pet(adoption_url="https://new-url.example/y")
        self.redirects_path.write_text(
            json.dumps({pet.pet_id: "https://old-url.example/x"})
        )

        run([FakeSource([pet])], [FakePoster()])

        redirects = json.loads(self.redirects_path.read_text())
        self.assertEqual(redirects[pet.pet_id], "https://old-url.example/x")
        self.assertEqual(pet.adoption_url, f"{SITE_URL}/r/?id={pet.pet_id}")

    def test_debug_posters_do_not_mint_redirects(self):
        pet = self._pet()
        adoption_url = pet.adoption_url

        run([FakeSource([pet])], [PosterDebug()])

        self.assertFalse(self.redirects_path.exists())
        self.assertEqual(pet.adoption_url, adoption_url)


class CreateSourcesTests(unittest.TestCase):
    def test_prod_returns_single_multi_species_rescuegroups_source(self):
        sources = create_sources(debug=False)

        self.assertEqual(len(sources), 1)
        self.assertIsInstance(sources[0], SourceRescueGroups)
        self.assertEqual(sources[0].species, ("dogs", "cats"))

    def test_debug_returns_manual_sources_for_dogs_and_cats(self):
        sources = create_sources(debug=True)

        self.assertEqual(len(sources), 2)
        self.assertIsInstance(sources[0], SourceManual)
        self.assertIsInstance(sources[1], SourceManual)
        self.assertEqual(sources[0].species, "dog")
        self.assertEqual(sources[1].species, "cat")


class CreatePostersTests(unittest.TestCase):
    def test_debug_returns_debug_poster(self):
        posters = create_posters(debug=True)

        self.assertEqual(len(posters), 1)
        self.assertEqual(posters[0].platform_name, "Debug")



if __name__ == "__main__":
    unittest.main()
