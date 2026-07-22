"""Live-API integration test for SourceRescueGroups.

Skipped unless CUTEPETSBOSTON_RESCUEGROUPS_API_KEY is set. This is the guard
against request-shape regressions like #124, where the hand-rolled body was
silently rejected by the live API and the bot fetched zero pets: unit tests
can't catch a body the real API refuses, only a real call can.

Run locally with:
    CUTEPETSBOSTON_RESCUEGROUPS_API_KEY=... pytest tests/test_rescue_groups_live.py
"""

import os

import pytest

from adoption_sources.rescue_groups import SourceRescueGroups

requires_api_key = pytest.mark.skipif(
    not os.environ.get("CUTEPETSBOSTON_RESCUEGROUPS_API_KEY"),
    reason="CUTEPETSBOSTON_RESCUEGROUPS_API_KEY not set",
)


@requires_api_key
def test_live_multi_species_search_returns_usable_pets():
    source = SourceRescueGroups()
    pets = list(source.fetch_pets())

    # The whole point of the search: the live API accepted the request shape
    # and returned records (a rejected body historically yielded zero).
    assert pets, "live search returned no pets — request shape likely rejected"

    assert {pet.species for pet in pets} <= {"dog", "cat"}
    for pet in pets:
        assert pet.name
        assert pet.pet_id

    # The bot can only post pets with an image and a link; if parsing lost
    # these for every record the run would fail even with a 200 response.
    postable = [pet for pet in pets if pet.image_url and pet.adoption_url]
    assert postable, "no pet had both an image and an adoption URL"
