"""Test utilities for working with sample data from a.json."""

import json
from pathlib import Path
from typing import Dict, Any

from abstractions import AdoptablePet


def load_sample_data() -> list[Dict[str, Any]]:
    """Load sample pet data from tests/fixtures/sample_data.json."""
    tests_dir = Path(__file__).parent
    data_file = tests_dir / "fixtures" / "sample_data.json"

    if not data_file.exists():
        raise FileNotFoundError(f"Sample data file not found: {data_file}")

    with open(data_file, 'r', encoding='utf-8') as f:
        return json.load(f)


def rescuegroups_to_adoptable_pet(animal_data: Dict[str, Any]) -> AdoptablePet:
    """Convert RescueGroups API animal data to AdoptablePet."""
    attributes = animal_data.get("attributes", {})
    name = attributes.get("name", "Unknown")

    # Clean up the name (remove special characters and promotional text)
    clean_name = name.split("***")[0].strip() if "***" in name else name
    clean_name = clean_name.split("*")[0].strip() if "*" in clean_name else clean_name

    species = "dog"
    breed = attributes.get("breedString", "Mixed")
    location = "Boston, MA"
    description = (attributes.get("descriptionText") or "")[:500]
    slug = attributes.get("slug", "")
    adoption_url = f"https://www.rescuegroups.org/pet/{slug}" if slug else None
    image_url = attributes.get("pictureThumbnailUrl")

    return AdoptablePet(
        name=clean_name,
        species=species,
        breed=breed,
        location=location,
        description=description,
        adoption_url=adoption_url,
        image_url=image_url,
    )


class RescueGroupsDataHelper:
    """Helper class for working with RescueGroups API data."""

    def __init__(self):
        self.sample_data = load_sample_data()

    def get_all_pets(self) -> list[AdoptablePet]:
        """Get all pets from sample data as AdoptablePet instances."""
        return [rescuegroups_to_adoptable_pet(animal) for animal in self.sample_data]

    def get_pet_by_name(self, name: str) -> AdoptablePet | None:
        """Get a specific pet by name."""
        for animal in self.sample_data:
            pet = rescuegroups_to_adoptable_pet(animal)
            if pet.name.lower() == name.lower():
                return pet
        return None

    def get_senior_pets(self) -> list[AdoptablePet]:
        """Get pets that are seniors."""
        senior_pets = []
        for animal in self.sample_data:
            attributes = animal.get("attributes", {})
            if attributes.get("ageGroup") == "Senior":
                senior_pets.append(rescuegroups_to_adoptable_pet(animal))
        return senior_pets

    def get_pets_by_size(self, size: str) -> list[AdoptablePet]:
        """Get pets by size group (Small, Medium, Large)."""
        pets_by_size = []
        for animal in self.sample_data:
            attributes = animal.get("attributes", {})
            if attributes.get("sizeGroup", "").lower() == size.lower():
                pets_by_size.append(rescuegroups_to_adoptable_pet(animal))
        return pets_by_size

    def get_raw_data(self) -> list[Dict[str, Any]]:
        """Get the raw sample data for testing data parsing."""
        return self.sample_data.copy()


# These classes can be run with or without pytest
class TestDataUtils:
    """Test cases for data utility functions."""

    def test_load_sample_data(self):
        """Test loading sample data from a.json."""
        data = load_sample_data()
        assert isinstance(data, list)
        assert len(data) > 0

        # Verify it's animal data
        for item in data:
            assert "type" in item
            assert item["type"] == "animals"
            assert "attributes" in item

    def test_rescuegroups_to_adoptable_pet_basic(self):
        """Test converting basic RescueGroups data to AdoptablePet."""
        sample_data = {
            "attributes": {
                "name": "Fluffy",
                "breedString": "Lab",
            }
        }
        pet = rescuegroups_to_adoptable_pet(sample_data)
        assert pet.name == "Fluffy"
        assert pet.breed == "Lab"

    def test_rescuegroups_to_adoptable_pet_with_promotions(self):
        """Test converting data with promotional text in name."""
        sample_data = {
            "attributes": {
                "name": "Doli ***Home for the Holidays 1/2 price!"
            }
        }
        pet = rescuegroups_to_adoptable_pet(sample_data)
        assert pet.name == "Doli"

    def test_rescuegroups_to_adoptable_pet_with_asterisks(self):
        """Test converting data with asterisks in name."""
        sample_data = {
            "attributes": {
                "name": "Cylana *Home for the holidays 1/2 price!"
            }
        }
        pet = rescuegroups_to_adoptable_pet(sample_data)
        assert pet.name == "Cylana"

    def test_rescuegroups_to_adoptable_pet_missing_name(self):
        """Test converting data with missing name."""
        sample_data = {"attributes": {}}
        pet = rescuegroups_to_adoptable_pet(sample_data)
        assert pet.name == "Unknown"


class TestRescueGroupsDataHelper:
    """Test cases for RescueGroupsDataHelper class."""

    def test_get_all_pets(self, data_helper):
        """Test getting all pets from sample data."""
        pets = data_helper.get_all_pets()
        assert len(pets) > 0
        assert all(isinstance(pet, AdoptablePet) for pet in pets)

    def test_get_pet_by_name(self, data_helper):
        """Test getting a specific pet by name."""
        pet = data_helper.get_pet_by_name("Doli")
        assert pet is not None
        assert pet.name == "Doli"

        pet = data_helper.get_pet_by_name("NonExistentPet")
        assert pet is None

    def test_get_senior_pets(self, data_helper):
        """Test getting senior pets."""
        senior_pets = data_helper.get_senior_pets()
        assert len(senior_pets) > 0
        assert all(isinstance(pet, AdoptablePet) for pet in senior_pets)

    def test_get_pets_by_size(self, data_helper):
        """Test getting pets by size."""
        large_pets = data_helper.get_pets_by_size("Large")
        small_pets = data_helper.get_pets_by_size("Small")

        assert len(large_pets) > 0
        assert len(small_pets) > 0
        assert all(isinstance(pet, AdoptablePet) for pet in large_pets)
        assert all(isinstance(pet, AdoptablePet) for pet in small_pets)

    def test_get_raw_data(self, data_helper):
        """Test getting raw sample data."""
        raw_data = data_helper.get_raw_data()
        assert isinstance(raw_data, list)
        assert len(raw_data) > 0

        raw_data.clear()
        assert len(data_helper.get_raw_data()) > 0


class TestWithSampleData:
    """Test cases using actual sample data from fixtures."""

    def test_sample_pets_from_api(self, data_helper):
        """Test getting pets from API sample data."""
        sample_pets_from_api = data_helper.get_all_pets()
        assert len(sample_pets_from_api) > 0
        assert all(isinstance(pet, AdoptablePet) for pet in sample_pets_from_api)

        pet_names = [pet.name for pet in sample_pets_from_api]
        assert "Doli" in pet_names
        assert "Kathy" in pet_names
        assert "Cylana" in pet_names

    def test_sample_data_structure(self):
        """Test the structure of sample RescueGroups data."""
        sample_rescuegroups_data = load_sample_data()
        assert len(sample_rescuegroups_data) == 3  # Should have 3 pets

        for animal in sample_rescuegroups_data:
            assert animal["type"] == "animals"
            assert "id" in animal
            assert "attributes" in animal
            assert "relationships" in animal

            attributes = animal["attributes"]
            assert "name" in attributes
            assert "breedString" in attributes
            assert "sex" in attributes


# Pytest fixtures (only used when pytest is available)
try:
    import pytest
    HAS_PYTEST = True

    @pytest.fixture
    def sample_rescuegroups_data():
        """Fixture providing raw RescueGroups API data."""
        return load_sample_data()

    @pytest.fixture
    def data_helper():
        """Fixture providing RescueGroupsDataHelper instance."""
        return RescueGroupsDataHelper()

    @pytest.fixture
    def sample_pets_from_api(data_helper):
        """Fixture providing AdoptablePet instances from API data."""
        return data_helper.get_all_pets()

except ImportError:
    # pytest not available, fixtures won't be available
    HAS_PYTEST = False

