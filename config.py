CITY_NAME = "Boston"
CITY_STATE = "MA"
CITY_HASHTAGS = ["Boston"]
POSTAL_CODE = "02108"

# Public site root (RFC 0001): redirect links are minted as
# {SITE_URL}/r/?id=<slug> so we own the hop and get click attribution.
SITE_URL = "https://www.cutepetsboston.com"

# RescueGroups API plural species names for the species we post about.
PET_SPECIES = ("dogs", "cats")

# Single-call limit; roughly matches two per-species calls at 25 each.
RESCUEGROUPS_LIMIT = 50
