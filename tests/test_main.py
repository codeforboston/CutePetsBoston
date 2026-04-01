import unittest
from unittest.mock import patch

from abstractions import AdoptablePet, Post, PostResult
from main import create_posters, run


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
        pet = AdoptablePet(
            name="Poppy",
            species="dog",
            breed="mutt",
            location="Boston, MA",
            image_url="https://example.com/poppy.jpg",
            adoption_url="https://example.com/adopt/poppy",
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


class CreatePostersTests(unittest.TestCase):
    def test_debug_returns_debug_poster(self):
        posters = create_posters(debug=True)

        self.assertEqual(len(posters), 1)
        self.assertEqual(posters[0].platform_name, "Debug")

    @patch.dict("os.environ", {"POSTER_PLATFORMS": "mastodon"}, clear=False)
    @patch("main._load_mastodon_poster")
    def test_platform_filter_returns_only_requested_platform(self, mock_loader):
        fake_poster = FakePoster()
        fake_poster.platform_name = "Mastodon"
        mock_loader.return_value = fake_poster

        posters = create_posters()

        self.assertEqual([poster.platform_name for poster in posters], ["Mastodon"])


if __name__ == "__main__":
    unittest.main()
