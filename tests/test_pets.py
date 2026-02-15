from typing import Iterable
from unittest.mock import Mock, MagicMock

from abstractions import AdoptablePet, PetSource, Post


def _pet(name: str, species: str = "dog", breed: str = "unknown", location: str = "Unknown", **kwargs) -> AdoptablePet:
    """Shortcut to create an AdoptablePet with required fields for tests."""
    return AdoptablePet(name=name, species=species, breed=breed, location=location, **kwargs)


# Try to import pytest, but don't fail if it's not available
try:
    import pytest
    HAS_PYTEST = True
except ImportError:
    HAS_PYTEST = False
    # Mock pytest for when it's not available
    class MockPytest:
        @staticmethod
        def fixture(*args, **kwargs):
            def decorator(func):
                return func
            return decorator
    pytest = MockPytest()
    PYTEST_AVAILABLE = False


class TestAdoptablePet:
    """Test cases for AdoptablePet dataclass."""

    def test_adoptable_pet_creation(self):
        """Test creating an AdoptablePet instance."""
        pet = _pet("Fluffy")
        assert pet.name == "Fluffy"

    def test_adoptable_pet_equality(self):
        """Test equality comparison of AdoptablePet instances."""
        pet1 = _pet("Fluffy")
        pet2 = _pet("Fluffy")
        pet3 = _pet("Spot")

        assert pet1 == pet2
        assert pet1 != pet3

    def test_adoptable_pet_string_representation(self):
        """Test string representation of AdoptablePet."""
        pet = _pet("Fluffy")
        assert pet.name == "Fluffy"
        assert "Fluffy" in str(pet)


class TestPost:
    """Test cases for Post dataclass."""

    def test_post_creation_text_only(self):
        """Test creating a Post with only text."""
        post = Post(text="Check out this cute pet!")
        assert post.text == "Check out this cute pet!"
        assert post.image_url is None
        assert post.link is None

    def test_post_creation_with_image(self):
        """Test creating a Post with text and image."""
        post = Post(
            text="Check out this cute pet!",
            image_url="https://example.com/pet.jpg"
        )
        assert post.text == "Check out this cute pet!"
        assert post.image_url == "https://example.com/pet.jpg"
        assert post.link is None

    def test_post_creation_with_all_fields(self):
        """Test creating a Post with all fields."""
        post = Post(
            text="Check out this cute pet!",
            image_url="https://example.com/pet.jpg",
            link="https://example.com/adopt"
        )
        assert post.text == "Check out this cute pet!"
        assert post.image_url == "https://example.com/pet.jpg"
        assert post.link == "https://example.com/adopt"

    def test_post_equality(self):
        """Test equality comparison of Post instances."""
        post1 = Post(text="Hello", image_url="img.jpg")
        post2 = Post(text="Hello", image_url="img.jpg")
        post3 = Post(text="Different", image_url="img.jpg")

        assert post1 == post2
        assert post1 != post3


class MockPetSource:
    """Mock implementation of PetSource for testing."""

    def __init__(self, pets: list[AdoptablePet]):
        self.pets = pets

    def fetch_pets(self) -> Iterable[AdoptablePet]:
        """Return the mock pets."""
        return self.pets


class MockSocialSink:
    """Mock implementation of SocialSink for testing."""

    def __init__(self):
        self.posted_content = []

    def post(self, post: Post) -> None:
        """Store the posted content for verification."""
        self.posted_content.append(post)


class TestPetSourceProtocol:
    """Test cases for PetSource protocol implementations."""

    def test_mock_pet_source_empty(self):
        """Test MockPetSource with no pets."""
        source = MockPetSource([])
        pets = list(source.fetch_pets())
        assert len(pets) == 0

    def test_mock_pet_source_single_pet(self):
        """Test MockPetSource with one pet."""
        expected_pet = _pet("Fluffy")
        source = MockPetSource([expected_pet])
        pets = list(source.fetch_pets())

        assert len(pets) == 1
        assert pets[0] == expected_pet

    def test_mock_pet_source_multiple_pets(self):
        """Test MockPetSource with multiple pets."""
        expected_pets = [_pet("Fluffy"), _pet("Spot"), _pet("Rex")]
        source = MockPetSource(expected_pets)
        pets = list(source.fetch_pets())

        assert len(pets) == 3
        assert pets == expected_pets

    def test_pet_source_protocol_compliance(self):
        """Test that MockPetSource implements PetSource protocol."""
        # This test verifies protocol compliance at runtime
        source = MockPetSource([_pet("Test")])

        # Should be able to call fetch_pets without type errors
        pets = source.fetch_pets()
        assert hasattr(pets, '__iter__')


class TestSocialSinkProtocol:
    """Test cases for SocialSink protocol implementations."""

    def test_mock_social_sink_single_post(self):
        """Test MockSocialSink with one post."""
        sink = MockSocialSink()
        post = Post(text="Test post")

        sink.post(post)

        assert len(sink.posted_content) == 1
        assert sink.posted_content[0] == post

    def test_mock_social_sink_multiple_posts(self):
        """Test MockSocialSink with multiple posts."""
        sink = MockSocialSink()
        posts = [
            Post(text="First post"),
            Post(text="Second post", image_url="img.jpg"),
            Post(text="Third post", link="link.com")
        ]

        for post in posts:
            sink.post(post)

        assert len(sink.posted_content) == 3
        assert sink.posted_content == posts

    def test_social_sink_protocol_compliance(self):
        """Test that MockSocialSink implements SocialSink protocol."""
        sink = MockSocialSink()
        post = Post(text="Test")

        # Should be able to call post without type errors
        result = sink.post(post)
        assert result is None  # post method returns None


class TestIntegration:
    """Integration test cases combining multiple components."""

    def test_pets_to_posts_workflow(self):
        """Test a typical workflow from pets to social posts."""
        # Setup: Create pets and mock services
        pets = [_pet("Fluffy the Cat"), _pet("Spot the Dog")]
        pet_source = MockPetSource(pets)
        social_sink = MockSocialSink()

        # Simulate a simple posting workflow
        fetched_pets = list(pet_source.fetch_pets())

        for pet in fetched_pets:
            post = Post(
                text=f"Meet {pet.name}! This adorable pet is looking for a home.",
                link="https://example.com/adopt"
            )
            social_sink.post(post)

        # Verify results
        assert len(social_sink.posted_content) == 2
        assert "Fluffy the Cat" in social_sink.posted_content[0].text
        assert "Spot the Dog" in social_sink.posted_content[1].text

        for post in social_sink.posted_content:
            assert post.link == "https://example.com/adopt"


# Pytest fixtures for common test data
@pytest.fixture
def sample_pets():
    """Fixture providing sample pets for testing."""
    return [_pet("Fluffy"), _pet("Spot"), _pet("Rex"), _pet("Bella")]


@pytest.fixture
def sample_posts():
    """Fixture providing sample posts for testing."""
    return [
        Post(text="Simple post"),
        Post(text="Post with image", image_url="https://example.com/image.jpg"),
        Post(text="Complete post", image_url="https://example.com/image.jpg", link="https://example.com/link"),
    ]


@pytest.fixture
def pet_source(sample_pets):
    """Fixture providing a MockPetSource with sample pets."""
    return MockPetSource(sample_pets)


@pytest.fixture
def social_sink():
    """Fixture providing a MockSocialSink."""
    return MockSocialSink()


class TestWithFixtures:
    """Test cases using pytest fixtures."""

    def test_pet_source_fixture(self, pet_source, sample_pets):
        """Test that pet_source fixture works correctly."""
        pets = list(pet_source.fetch_pets())
        assert pets == sample_pets

    def test_social_sink_fixture(self, social_sink, sample_posts):
        """Test that social_sink fixture works correctly."""
        for post in sample_posts:
            social_sink.post(post)

        assert len(social_sink.posted_content) == len(sample_posts)
        assert social_sink.posted_content == sample_posts

