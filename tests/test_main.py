import json
from pathlib import Path
import sqlite3
from tempfile import TemporaryDirectory
import unittest

from abstractions import AdoptablePet, Post, PostMetrics, PostResult
from adoption_sources import SourceManual
from adoption_sources.rescue_groups import SourceRescueGroups
from main import create_collectors, create_posters, create_sources, run


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
        return PostResult(
            success=True,
            post_id=f"post-{len(self.posts)}",
            post_url=f"https://example.com/posts/{len(self.posts)}",
        )


class FakeCollector:
    platform_name = "FakePoster"

    def __init__(self):
        self.calls = []

    def fetch_metrics(self, post_id, post_url=None):
        self.calls.append((post_id, post_url))
        return PostMetrics(
            collected_at="set-by-run",
            likes=3,
            reposts=1,
            comments=2,
        )


class RunFlowTests(unittest.TestCase):
    def test_run_calls_source_posters_and_collectors(self):
        pet = AdoptablePet(
            name="Poppy",
            species="dog",
            breed="mutt",
            location="Boston, MA",
            image_url="https://example.com/poppy.jpg",
            adoption_url="https://example.com/adopt/poppy",
            pet_id="pet-poppy",
        )
        source = FakeSource([pet])
        poster_one = FakePoster()
        poster_two = FakePoster()
        collector = FakeCollector()

        with TemporaryDirectory() as temporary_directory:
            database_path = Path(temporary_directory) / "database.json"
            metrics_db_path = Path(temporary_directory) / "metrics.sqlite"
            results = run(
                [source],
                [poster_one, poster_two],
                collectors=[collector],
                database_path=database_path,
                metrics_db_path=metrics_db_path,
            )
            data = json.loads(database_path.read_text())
            with sqlite3.connect(metrics_db_path) as conn:
                rows = conn.execute("SELECT likes FROM post_metrics").fetchall()

        self.assertTrue(source.fetch_called)
        self.assertTrue(poster_one.format_called)
        self.assertTrue(poster_one.publish_called)
        self.assertTrue(poster_two.format_called)
        self.assertTrue(poster_two.publish_called)
        self.assertEqual(len(results), 2)
        self.assertEqual(len(data["posted_pets"]), 1)
        self.assertEqual(len(data["posts"]), 2)
        self.assertEqual(len(collector.calls), 2)
        self.assertEqual(data["posts"][0]["metrics"][0]["likes"], 3)
        self.assertEqual(rows[0][0], 3)

    def test_run_with_mixed_species_pool(self):
        dog = AdoptablePet(
            name="Rex",
            species="dog",
            breed="mutt",
            location="Boston, MA",
            image_url="https://example.com/rex.jpg",
            adoption_url="https://example.com/adopt/rex",
            pet_id="test-dog",
        )
        cat = AdoptablePet(
            name="Luna",
            species="cat",
            breed="tabby",
            location="Boston, MA",
            image_url="https://example.com/luna.jpg",
            adoption_url="https://example.com/adopt/luna",
            pet_id="test-cat",
        )
        source = FakeSource([dog, cat])
        poster = FakePoster()

        with TemporaryDirectory() as temporary_directory:
            database_path = Path(temporary_directory) / "database.json"
            results = run(
                [source],
                [poster],
                collectors=[],
                database_path=database_path,
            )
            data = json.loads(database_path.read_text())

        self.assertTrue(poster.format_called)
        self.assertTrue(poster.publish_called)
        self.assertEqual(len(results), 1)
        self.assertEqual(len(data["posted_pets"]), 1)
        self.assertIn(data["posted_pets"][0]["pet_id"], {"test-dog", "test-cat"})


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

    def test_debug_disables_metric_collectors(self):
        self.assertEqual(create_collectors(debug=True), [])


if __name__ == "__main__":
    unittest.main()
