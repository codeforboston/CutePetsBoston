"""Social media poster implementations implementing the SocialPoster interface."""

__all__ = ["PosterBluesky", "PosterDebug", "PosterMastodon", "PosterInstagram"]


def __getattr__(name):
    if name == "PosterBluesky":
        from social_posters.bluesky import PosterBluesky

        return PosterBluesky
    if name == "PosterDebug":
        from social_posters.debug import PosterDebug

        return PosterDebug
    if name == "PosterInstagram":
        from social_posters.instagram import PosterInstagram

        return PosterInstagram
    if name == "PosterMastodon":
        from social_posters.mastodon import PosterMastodon

        return PosterMastodon
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
