"""Pure helpers for turning dog-breed text into social-media hashtag names."""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable


def extract_dog_breed_tags(text: str | None, dog_breeds: Iterable[str]) -> list[str]:
    """Return the specific dog-breed hashtags found in *text*.

    ``dog_breeds`` is a plain iterable of breed names, typically the ``dogs``
    list in ``dog_breeds.json``. If a matched name is contained within a longer
    matched name, only the longer, more specific breed is returned.
    """
    if not text:
        return []

    matches: dict[str, tuple[str, int, int]] = {}
    for breed in dog_breeds:
        if not isinstance(breed, str) or not breed:
            continue
        match = _find_phrase(text, breed)
        if match:
            matches[breed] = (match.group(), len(match.group()), match.start())

    specific_breeds = [
        breed
        for breed, (matched_phrase, _, _) in matches.items()
        if not any(
            breed != other_breed
            and _is_phrase_within(matched_phrase, other_breed)
            and _normalized_length(other_breed) > _normalized_length(breed)
            for other_breed in matches
        )
    ]
    specific_breeds.sort(key=lambda breed: matches[breed][2])
    return [_hashtag_name(breed) for breed in specific_breeds]


def _find_phrase(text: str, phrase: str) -> re.Match[str] | None:
    words = [re.escape(word) for word in re.split(r"[\s-]+", phrase.strip()) if word]
    return (
        re.search(r"(?<!\w)" + r"[\s-]+".join(words) + r"(?!\w)", text, re.IGNORECASE)
        if words
        else None
    )


def _is_phrase_within(phrase: str, breed: str) -> bool:
    return _find_phrase(breed, phrase) is not None


def _normalized_length(value: str) -> int:
    return len(re.sub(r"[^a-z0-9]", "", value.casefold()))


def _hashtag_name(breed: str) -> str:
    normalized = unicodedata.normalize("NFKD", breed).encode("ascii", "ignore").decode()
    return "".join(part.capitalize() for part in re.findall(r"[A-Za-z0-9]+", normalized))
