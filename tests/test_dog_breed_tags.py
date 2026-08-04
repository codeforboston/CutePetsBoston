import json
from pathlib import Path

from dog_breed_tags import extract_dog_breed_tags


DOG_BREEDS = json.loads(
    (Path(__file__).parent.parent / "dog_breeds.json").read_text(encoding="utf-8")
)["dogs"]


def test_extracts_multiple_breeds_from_listing_text():
    assert extract_dog_breed_tags(
        "Labrador Retriever / Akita / Mixed (short coat)", DOG_BREEDS
    ) == ["LabradorRetriever", "Akita"]


def test_specific_breed_suppresses_component_matches():
    dog_breeds = ["Labrador Retriever", "Labrador", "Retriever"]
    assert extract_dog_breed_tags("Labrador Retriever mix", dog_breeds) == [
        "LabradorRetriever"
    ]


def test_hyphenated_breed_matches_space_separated_text():
    assert extract_dog_breed_tags("A sweet Chinese Shar Pei mix", DOG_BREEDS) == [
        "ChineseSharPei"
    ]


def test_does_not_match_a_breed_inside_another_word():
    assert extract_dog_breed_tags("The houndstooth blanket is lovely", DOG_BREEDS) == []


def test_empty_or_unknown_text_has_no_breed_tags():
    assert extract_dog_breed_tags(None, DOG_BREEDS) == []
    assert extract_dog_breed_tags("Mixed breed", DOG_BREEDS) == []
