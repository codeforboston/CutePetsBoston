import unittest

from source_manual import MANUAL_SOURCE_DATA, SourceManual


class SourceManualTests(unittest.TestCase):
    def test_fetch_returns_all_manual_pets(self):
        source = SourceManual()

        pets = list(source.fetch_pets())

        self.assertEqual(len(pets), len(MANUAL_SOURCE_DATA))
        names = {pet.name for pet in pets}
        self.assertSetEqual(names, {"Doli", "Kathy", "Cylana"})
        for pet in pets:
            self.assertTrue(pet.image_url)
            self.assertTrue(pet.adoption_url)


if __name__ == "__main__":
    unittest.main()
