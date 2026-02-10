from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Iterable


# =============================================================================
# Pet Ingestor Interface
# =============================================================================


@dataclass
class AdoptablePet:
    """Represents a pet available for adoption."""

    name: str
    species: str  # "dog" or "cat"
    breed: str
    location: str
    description: str = ""
    adoption_url: str | None = None
    image_url: str | None = None


class PetSource(ABC):
    """Interface for fetching pets from various adoption APIs."""

    @property
    @abstractmethod
    def source_name(self) -> str:
        """Return the name of the pet source."""
        ...

    @abstractmethod
    def fetch_pets(self) -> Iterable[AdoptablePet]:
        """Fetch available pets from the source."""
        ...


# =============================================================================
# Social Media Poster Interface
# =============================================================================


@dataclass
class Post:
    """Represents a social media post about an adoptable pet."""

    text: str
    image_url: str | None = None
    link: str | None = None
    alt_text: str | None = None  # For image accessibility
    tags: list[str] = field(default_factory=list)


@dataclass
class PostResult:
    """Result of attempting to publish a post."""

    success: bool
    post_id: str | None = None
    post_url: str | None = None
    error_message: str | None = None


class SocialPoster(ABC):
    """
    Abstract base class for social media platform implementations.

    Concrete implementations should inherit from this class and implement
    the abstract methods for their specific platform (e.g., Bluesky, Instagram).
    """

    @property
    @abstractmethod
    def platform_name(self) -> str:
        """Return the name of the social media platform."""
        ...

    @abstractmethod
    def authenticate(self) -> bool:
        """
        Authenticate with the platform.

        Returns:
            True if authentication was successful, False otherwise.
        """
        ...

    @abstractmethod
    def publish(self, post: Post) -> PostResult:
        """
        Publish a post to the platform.

        Args:
            post: The post to publish.

        Returns:
            PostResult indicating success/failure and relevant details.
        """
        ...

    def is_authenticated(self) -> bool:
        """Check if currently authenticated. Override if platform supports this."""
        return False

    def format_post(self, pet: AdoptablePet) -> Post:
        """
        Create a Post from an AdoptablePet.

        Override this method to customize post formatting for specific platforms.
        """
        text = f"Meet {pet.name}! This adorable {pet.breed} {pet.species} is looking for a forever home in {pet.location}."
        if pet.description:
            text += f"\n\n{pet.description}"
        if pet.adoption_url:
            text += f"\n\nAdopt {pet.name}: {pet.adoption_url}"

        return Post(
            text=text,
            image_url=pet.image_url,
            link=pet.adoption_url,
            alt_text=f"Photo of {pet.name}, a {pet.breed} {pet.species} available for adoption",
            tags=[
                "adoptdontshop",
                "rescue",
                pet.species,
                pet.breed.lower().replace(" ", ""),
            ],
        )
