import os

#  Import environment variables and fallback to defaults for Boston if not found.
CITY_NAME = os.environ.get("CITY_NAME", "Boston")
CITY_STATE = os.environ.get("CITY_STATE", "MA")
CITY_HASHTAGS = [CITY_NAME]
POSTAL_CODE = os.environ.get("POSTAL_CODE", "02108")

# Public site root (RFC 0001): redirect links are minted as
# {SITE_URL}/r/?id=<slug> so we own the hop and get click attribution.
SITE_URL = "https://www.cutepetsboston.com"

# Every species we know how to post, keyed by RescueGroups plural name
# (lowercased) -> singular name used in posts and hashtags. To support a new
# species, add it here; names must match RescueGroups' species list.
SUPPORTED_SPECIES: dict[str, str] = {
    "dogs": "dog",
    "cats": "cat",
    "rabbits": "rabbit",
    "chinchillas": "chinchilla",
    "guinea pigs": "guinea pig",
    "hamsters": "hamster",
    "gerbils": "gerbil",
    "ferrets": "ferret",
    "rats": "rat",
    "mice": "mouse",
    "degus": "degu",
    "hedgehogs": "hedgehog",
}

# Species posted by default. Override with the CUTEPETSBOSTON_PET_SPECIES env
# var or main.py's --species flag, e.g. "chinchillas" or "rabbits,chinchillas".
PET_SPECIES = ("dogs", "cats")
PET_SPECIES_ENV_VAR = "CUTEPETSBOSTON_PET_SPECIES"


def parse_species(value: str) -> tuple[str, ...]:
    """Parse a comma-separated species list, e.g. "chinchillas, Guinea Pigs".

    Returns de-duplicated plural names in order. Raises ValueError for empty
    input or a species missing from SUPPORTED_SPECIES.
    """
    names = tuple(dict.fromkeys(n.strip().lower() for n in value.split(",") if n.strip()))
    if not names:
        raise ValueError("At least one species is required")
    unknown = [n for n in names if n not in SUPPORTED_SPECIES]
    if unknown:
        raise ValueError(f"Unsupported species: {', '.join(unknown)}. Supported: {', '.join(SUPPORTED_SPECIES)}")
    return names


# Single-call limit; roughly matches two per-species calls at 25 each.
RESCUEGROUPS_LIMIT = 50
