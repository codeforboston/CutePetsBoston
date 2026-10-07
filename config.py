import os

#  Import environment variables and fallback to defaults for Boston if not found. 
CITY_NAME = os.environ.get("CITY_NAME", "Boston")
CITY_STATE = os.environ.get("CITY_STATE", "MA")
CITY_HASHTAGS = [CITY_NAME]
POSTAL_CODE = os.environ.get("POSTAL_CODE", "02108")

# RescueGroups API plural species names for the species we post about.
PET_SPECIES = ("dogs", "cats")

# Single-call limit; roughly matches two per-species calls at 25 each.
RESCUEGROUPS_LIMIT = 50
