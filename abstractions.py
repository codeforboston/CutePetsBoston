from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from functools import cached_property
from typing import Iterable, Protocol

from config import CITY_NAME, CITY_STATE

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
    image_urls: list[str] = field(default_factory=list)
    age_string: str | None = None
    sex: str | None = None
    size_group: str | None = None
    pet_id: str | None = None
    rescue_id: str | None = None  # shelter's own animal id (RescueGroups "rescueId")

    def __post_init__(self) -> None:
        self.image_urls = select_image_urls(self.image_urls)


class PetProvider(Protocol):
    """The pet-source capability required by orchestration."""

    @abstractmethod
    def fetch_pets(self) -> Iterable[AdoptablePet]:
        """Fetch available pets from the source."""
        ...


class PetSource(PetProvider, ABC):
    """A pet provider with an identifying source name."""

    @property
    @abstractmethod
    def source_name(self) -> str:
        """Return the name of the pet source."""
        ...


# =============================================================================
# Social Media Poster Interface
# =============================================================================


@dataclass
class Post:
    """Represents a social media post about an adoptable pet."""

    text: str
    image_urls: list[str] = field(default_factory=list)
    link: str | None = None
    alt_text: str | None = None  # For image accessibility
    tags: list[str] = field(default_factory=list)

    @cached_property
    def selected_image_urls(self) -> list[str]:
        """Return up to four distinct photo URLs in their original order."""
        return select_image_urls(self.image_urls)


MAX_POST_IMAGES = 4


def select_image_urls(image_urls: list[str]) -> list[str]:
    """Return up to four distinct photo URLs in their original order."""
    return list(dict.fromkeys(url for url in image_urls if url))[:MAX_POST_IMAGES]


@dataclass
class PostResult:
    """Result of attempting to publish a post."""

    success: bool
    post_id: str | None = None
    post_url: str | None = None
    error_message: str | None = None


class NamedPlatform(Protocol):
    @property
    @abstractmethod
    def platform_name(self) -> str:
        """Return the platform name used in persisted post records."""
        ...


class PostPublisher(NamedPlatform, Protocol):
    """The formatting and publishing capabilities required by orchestration."""

    @abstractmethod
    def format_post(self, pet: AdoptablePet) -> Post:
        """Create a platform-specific post from a pet."""
        ...

    @abstractmethod
    def publish(self, post: Post) -> PostResult:
        """Publish a post and return its success or failure result."""
        ...


class SocialPoster(PostPublisher, ABC):
    """A publisher with authentication hooks and default post formatting.

    Concrete platform implementations inherit the capability contract from
    PostPublisher and implement its abstract methods along with authenticate.
    """

    @abstractmethod
    def authenticate(self) -> bool:
        """
        Authenticate with the platform.

        Returns:
            True if authentication was successful, False otherwise.
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
        text = (
            f"Meet {pet.name}! This adorable {pet.breed} {pet.species} is looking for a forever home in {pet.location}."
        )
        if pet.description:
            text += f"\n\n{pet.description}"
        if pet.adoption_url:
            text += f"\n\nAdopt {pet.name}: {pet.adoption_url}"

        city = ""
        if pet.location != f"{CITY_NAME}, {CITY_STATE}":
            city = pet.location.split(",")[0].capitalize()

        return Post(
            text=text,
            image_urls=pet.image_urls,
            link=pet.adoption_url,
            alt_text=f"Photo of {pet.name}, a {pet.breed} {pet.species} available for adoption",
            tags=[
                "adoptdontshop",
                "rescue",
                city,
                pet.species,
                pet.breed.lower().replace(" ", ""),
            ],
        )


# =============================================================================
# Engagement Metric Collector Interface
# =============================================================================


@dataclass
class PostMetrics:
    """Point-in-time engagement counts for a published post."""

    collected_at: str
    likes: int | None = None
    reposts: int | None = None
    comments: int | None = None


class MetricsProvider(NamedPlatform, Protocol):
    """The metric-collection capability required by orchestration."""

    @abstractmethod
    def fetch_metrics(self, post_id: str, post_url: str | None = None) -> PostMetrics | None:
        """Return a metric snapshot, or None when the post cannot be read."""
        ...


class MetricCollector(MetricsProvider, ABC):
    """Base class enforcing the shared metric-provider contract."""
