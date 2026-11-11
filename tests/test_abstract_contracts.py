"""Capability protocols retain runtime enforcement for explicit ABC subclasses."""

import pytest

from abstractions import MetricCollector, PetSource, SocialPoster


@pytest.mark.parametrize("base", [PetSource, SocialPoster, MetricCollector])
def test_incomplete_implementation_cannot_be_instantiated(base: type) -> None:
    class IncompleteImplementation(base):
        pass

    with pytest.raises(TypeError, match="abstract"):
        IncompleteImplementation()
