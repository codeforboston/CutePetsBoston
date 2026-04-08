import unittest

from adoption_sources import MANUAL_SOURCE_DATA, SourceManual


class SourceManualTests(unittest.TestCase):
    def test_fetch_returns_all_manual_pets(self):
        source = SourceManual()

        pets = list(source.fetch_pets())

        self.assertEqual(len(pets), len(MANUAL_SOURCE_DATA))
        names = {pet.name for pet in pets}
        expected_names = {d["attributes"]["name"] for d in MANUAL_SOURCE_DATA}
        self.assertSetEqual(names, expected_names)
        for pet in pets:
            self.assertTrue(pet.image_url)
            self.assertTrue(pet.adoption_url)


if __name__ == "__main__":
    unittest.main()
