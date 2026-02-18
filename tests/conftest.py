"""Shared pytest configuration and fixtures for the test suite."""

import pytest

from abstractions import AdoptablePet, Post
from tests.test_pets import MockPetSource, MockSocialSink
from tests.test_data_utils import RescueGroupsDataHelper


@pytest.fixture(scope="session")
def data_helper():
    """Session-scoped fixture providing RescueGroupsDataHelper instance."""
    return RescueGroupsDataHelper()


def _pet(name, species="dog", breed="unknown", location="Unknown", **kwargs):
    """Shortcut to create an AdoptablePet with required fields for tests."""
    return AdoptablePet(name=name, species=species, breed=breed, location=location, **kwargs)


@pytest.fixture
def sample_pets():
    """Fixture providing a list of sample AdoptablePet instances."""
    return [_pet("Fluffy"), _pet("Spot"), _pet("Rex"), _pet("Bella")]


@pytest.fixture
def sample_posts():
    """Fixture providing a list of sample Post instances."""
    return [
        Post(text="Simple post"),
        Post(text="Post with image", image_url="https://example.com/image.jpg"),
        Post(
            text="Complete post",
            image_url="https://example.com/image.jpg",
            link="https://example.com/link"
        ),
    ]


@pytest.fixture
def mock_pet_source(sample_pets):
    """Fixture providing a MockPetSource with sample pets."""
    return MockPetSource(sample_pets)


@pytest.fixture
def mock_social_sink():
    """Fixture providing a MockSocialSink."""
    return MockSocialSink()


@pytest.fixture
def real_pets_from_api(data_helper):
    """Fixture providing real AdoptablePet instances from API sample data."""
    return data_helper.get_all_pets()


@pytest.fixture
def empty_pet_source():
    """Fixture providing an empty MockPetSource."""
    return MockPetSource([])


@pytest.fixture
def single_pet():
    """Fixture providing a single AdoptablePet instance."""
    return _pet("TestPet")


@pytest.fixture
def single_pet_source(single_pet):
    """Fixture providing a MockPetSource with a single pet."""
    return MockPetSource([single_pet])

