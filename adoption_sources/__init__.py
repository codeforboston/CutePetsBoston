"""Adoption pet sources implementing the PetSource interface."""

from adoption_sources.manual import MANUAL_SOURCE_DATA, SourceManual
from adoption_sources.rescue_groups import SourceRescueGroups

__all__ = ["SourceRescueGroups", "SourceManual", "MANUAL_SOURCE_DATA"]
