import json
from pathlib import Path

from dog_breed_tags import extract_dog_breed_tags

DOG_BREEDS = json.loads(
    (Path(__file__).parent.parent / "dog_breeds.json").read_text(encoding="utf-8")
)["dogs"]

def test_ignores_breeds_not_in_catalog():
    assert extract_dog_breed_tags(
        "Labrador Retriever / Prairie Dog / Mixed (short coat)", DOG_BREEDS
    ) == ["LabradorRetriever"]

def test_specific_breed_suppresses_component_matches():
    dog_breeds = ["Labrador Retriever", "Labrador", "Retriever"]
    assert extract_dog_breed_tags("Labrador Retriever mix", dog_breeds) == [
        "LabradorRetriever"
    ]

def test_extracts_catalog_breed_within_unlisted_breed_name():
    assert extract_dog_breed_tags("A sweet Chinese Shar Pei mix", DOG_BREEDS) == [
        "SharPei"
    ]

def test_does_not_match_a_breed_inside_another_word():
    assert extract_dog_breed_tags("labradorretriever/bordercollie/mixed(shortcoat)", DOG_BREEDS) == [
        "LabradorRetriever",
        "BorderCollie",
    ]

def test_does_not_match_a_breed_inside_another_word():
    assert extract_dog_breed_tags("The houndstooth blanket is lovely", DOG_BREEDS) == []

def test_empty_or_unknown_text_has_no_breed_tags():
    assert extract_dog_breed_tags(None, DOG_BREEDS) == []
    assert extract_dog_breed_tags("Mixed breed", DOG_BREEDS) == []
