"""Adoption pet sources implementing the PetSource interface."""

from adoption_sources.manual import SourceManual
from adoption_sources.rescue_groups import SourceRescueGroups

__all__ = ["SourceRescueGroups", "SourceManual"]
