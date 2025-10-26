from typing import Dict, Literal

# Define safety level constants for consistency and clarity
SafetyLevel = Literal["Safe", "Caution", "Dangerous", "Unknown"]

SAFETY_LEVEL_SAFE: SafetyLevel = "Safe"
SAFETY_LEVEL_CAUTION: SafetyLevel = "Caution"
SAFETY_LEVEL_DANGEROUS: SafetyLevel = "Dangerous"
SAFETY_LEVEL_UNKNOWN: SafetyLevel = "Unknown"

# A predefined dictionary of known animal safety ratings.
# This can be expanded or moved to a configuration file later.
_ANIMAL_SAFETY_RATINGS: Dict[str, SafetyLevel] = {
    "zebra": SAFETY_LEVEL_SAFE,
    "giraffe": SAFETY_LEVEL_SAFE,
    "wildebeest": SAFETY_LEVEL_SAFE,
    "impala": SAFETY_LEVEL_SAFE,
    "warthog": SAFETY_LEVEL_CAUTION,
    "baboon": SAFETY_LEVEL_CAUTION,
    "hyena": SAFETY_LEVEL_CAUTION,
    "elephant": SAFETY_LEVEL_DANGEROUS,
    "lion": SAFETY_LEVEL_DANGEROUS,
    "leopard": SAFETY_LEVEL_DANGEROUS,
    "buffalo": SAFETY_LEVEL_DANGEROUS,
    "rhino": SAFETY_LEVEL_DANGEROUS,
    "hippopotamus": SAFETY_LEVEL_DANGEROUS,
}

def get_animal_safety_rating(animal_name: str) -> SafetyLevel:
    """
    Determines the safety rating for a given animal based on a predefined list.

    This function provides a general safety classification for common safari animals
    to be used in guest briefings and activity planning.

    Args:
        animal_name: The common name of the animal (case-insensitive).

    Returns:
        A safety level string: "Safe", "Caution", "Dangerous", or "Unknown"
        if the animal is not in the predefined list.
    """
    normalized_name = animal_name.lower().strip()
    return _ANIMAL_SAFETY_RATINGS.get(normalized_name, SAFETY_LEVEL_UNKNOWN)
