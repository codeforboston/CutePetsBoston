import unittest
import uuid

from abstractions import AdoptablePet, Post, PostResult
from adoption_sources import SourceManual
from adoption_sources.rescue_groups import SourceRescueGroups
from main import create_posters, create_sources, run


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


class RunFlowTests(unittest.TestCase):
    def test_run_calls_source_and_posters(self):
        pet_id = f"test-poppy-{uuid.uuid4()}"
        pet = AdoptablePet(
            name="Poppy",
            species="dog",
            breed="mutt",
            location="Boston, MA",
            image_url="https://example.com/poppy.jpg",
            adoption_url="https://example.com/adopt/poppy",
            pet_id=pet_id,
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


class CreateSourcesTests(unittest.TestCase):
    def test_prod_returns_rescuegroups_for_each_species(self):
        sources = create_sources(debug=False)

        self.assertEqual(len(sources), 2)
        self.assertIsInstance(sources[0], SourceRescueGroups)
        self.assertIsInstance(sources[1], SourceRescueGroups)
        self.assertEqual(sources[0].species, "dogs")
        self.assertEqual(sources[1].species, "cats")

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
