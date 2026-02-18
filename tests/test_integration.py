"""Integration tests for the pets module using real sample data."""

import pytest
from abstractions import AdoptablePet, Post
from tests.test_pets import MockPetSource, MockSocialSink
from tests.test_data_utils import RescueGroupsDataHelper


class TestRealDataIntegration:
    """Integration tests using real sample data from a.json."""

    def test_end_to_end_with_sample_data(self, data_helper, mock_social_sink):
        """Test complete workflow from sample data to social posts."""
        # Get pets from sample data
        pets = data_helper.get_all_pets()
        pet_source = MockPetSource(pets)

        # Create and post content for each pet
        fetched_pets = list(pet_source.fetch_pets())
        for pet in fetched_pets:
            post = Post(
                text=f"🐾 Meet {pet.name}! This sweet pet is looking for their forever home. Could it be with you?",
                link="https://angelsrescue.org/adopt"
            )
            mock_social_sink.post(post)

        # Verify posts were created
        assert len(mock_social_sink.posted_content) == len(pets)

        # Check that all expected pets are mentioned
        posted_texts = [post.text for post in mock_social_sink.posted_content]
        for pet in pets:
            assert any(pet.name in text for text in posted_texts)

    def test_senior_pets_workflow(self, data_helper, mock_social_sink):
        """Test workflow specifically for senior pets."""
        senior_pets = data_helper.get_senior_pets()
        pet_source = MockPetSource(senior_pets)

        # Create special posts for senior pets
        for pet in pet_source.fetch_pets():
            post = Post(
                text=f"💝 Senior spotlight: {pet.name} has so much love to give! Senior pets make wonderful companions.",
                link="https://angelsrescue.org/adopt"
            )
            mock_social_sink.post(post)

        # Should have posts for all senior pets
        assert len(mock_social_sink.posted_content) == len(senior_pets)

        # All posts should mention senior/Senior
        for post in mock_social_sink.posted_content:
            assert "Senior" in post.text or "senior" in post.text

    def test_size_based_posting(self, data_helper, mock_social_sink):
        """Test workflow for different size categories."""
        small_pets = data_helper.get_pets_by_size("Small")
        large_pets = data_helper.get_pets_by_size("Large")

        # Post small pets with apartment-friendly messaging
        for pet in small_pets:
            post = Post(
                text=f"🏠 {pet.name} is perfect for apartment living! Small size, big personality!",
                link="https://angelsrescue.org/adopt"
            )
            mock_social_sink.post(post)

        # Post large pets with yard-friendly messaging
        for pet in large_pets:
            post = Post(
                text=f"🏡 {pet.name} is a beautiful large breed looking for a home with space to roam!",
                link="https://angelsrescue.org/adopt"
            )
            mock_social_sink.post(post)

        total_expected_posts = len(small_pets) + len(large_pets)
        assert len(mock_social_sink.posted_content) == total_expected_posts

    def test_data_quality_validation(self, data_helper):
        """Test that sample data meets quality expectations."""
        pets = data_helper.get_all_pets()

        # Should have pets from the sample data
        assert len(pets) > 0

        # All pets should have non-empty names
        for pet in pets:
            assert pet.name
            assert pet.name.strip()
            assert pet.name != "Unknown"

        # Should have expected pets from a.json
        pet_names = [pet.name for pet in pets]
        assert "Doli" in pet_names
        assert "Kathy" in pet_names
        assert "Cylana" in pet_names

    def test_mock_implementations_with_real_data(self, real_pets_from_api):
        """Test that mock implementations work correctly with real data."""
        # Test MockPetSource with real pets
        pet_source = MockPetSource(real_pets_from_api)
        fetched_pets = list(pet_source.fetch_pets())

        assert len(fetched_pets) == len(real_pets_from_api)
        assert all(isinstance(pet, AdoptablePet) for pet in fetched_pets)

        # Test MockSocialSink with posts about real pets
        social_sink = MockSocialSink()
        for pet in fetched_pets[:2]:  # Just test with first 2 pets
            post = Post(text=f"Adopt {pet.name} today!")
            social_sink.post(post)

        assert len(social_sink.posted_content) == 2
        assert all(isinstance(post, Post) for post in social_sink.posted_content)


class TestErrorHandling:
    """Test error handling scenarios."""

    def test_empty_pet_source_workflow(self, mock_social_sink):
        """Test workflow with no available pets."""
        empty_source = MockPetSource([])
        pets = list(empty_source.fetch_pets())

        assert len(pets) == 0

        # Should handle empty case gracefully
        for pet in pets:  # This loop shouldn't execute
            post = Post(text=f"Meet {pet.name}")
            mock_social_sink.post(post)

        assert len(mock_social_sink.posted_content) == 0

    def test_malformed_pet_data_handling(self):
        """Test handling of edge cases in pet data."""
        # Test with unusual names
        unusual_pets = [
            AdoptablePet(name="", species="dog", breed="unknown", location="Unknown"),
            AdoptablePet(name="   ", species="dog", breed="unknown", location="Unknown"),
            AdoptablePet(name="A" * 100, species="dog", breed="unknown", location="Unknown"),
        ]

        pet_source = MockPetSource(unusual_pets)
        pets = list(pet_source.fetch_pets())

        # Should still work, even with unusual data
        assert len(pets) == 3
        assert all(isinstance(pet, AdoptablePet) for pet in pets)


class TestScalability:
    """Test scalability scenarios."""

    def test_large_number_of_pets(self):
        """Test handling a large number of pets."""
        # Create many pets
        many_pets = [
            AdoptablePet(name=f"Pet{i}", species="dog", breed="unknown", location="Unknown")
            for i in range(1000)
        ]
        pet_source = MockPetSource(many_pets)

        # Should handle large numbers efficiently
        pets = list(pet_source.fetch_pets())
        assert len(pets) == 1000

        # Test posting for many pets
        social_sink = MockSocialSink()
        for i, pet in enumerate(pets[:100]):  # Test first 100
            post = Post(text=f"Pet number {i}: {pet.name}")
            social_sink.post(post)

        assert len(social_sink.posted_content) == 100

    def test_repeated_operations(self, real_pets_from_api):
        """Test repeated operations on the same data."""
        pet_source = MockPetSource(real_pets_from_api)

        # Fetch pets multiple times
        for _ in range(10):
            pets = list(pet_source.fetch_pets())
            assert len(pets) == len(real_pets_from_api)
            assert pets == real_pets_from_api

