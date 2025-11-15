import random
from enum import Enum
from typing import Dict, Union

class WeatherCondition(str, Enum):
    """Enumeration for weather conditions."""
    SUNNY = "sunny"
    RAINY = "rainy"
    CLOUDY = "cloudy"
    NIGHT = "night"

# Base sighting probabilities (out of 100) for common safari animals.
# These are purely fictional for this example.
BASE_PROBABILITIES: Dict[str, int] = {
    "lion": 30,
    "elephant": 60,
    "giraffe": 55,
    "zebra": 70,
    "rhino": 15,
    "leopard": 10,
    "hippo": 40,
}

# Weather modifiers. These values are added to the base probability.
WEATHER_MODIFIERS: Dict[WeatherCondition, Dict[str, int]] = {
    WeatherCondition.SUNNY: {
        "lion": -5,
        "elephant": 5,
        "hippo": 15, # More likely to be in water, visible
        "leopard": -8,
    },
    WeatherCondition.RAINY: {
        "lion": -10,
        "elephant": -5,
        "rhino": 10,
        "hippo": -10,
        "zebra": -15,
    },
    WeatherCondition.CLOUDY: {
        "lion": 15, # More active when not too hot
        "rhino": 5,
        "leopard": 5,
    },
    WeatherCondition.NIGHT: {
        "lion": 25,
        "rhino": 15,
        "leopard": 30, # Nocturnal
        "elephant": -20,
        "giraffe": -20,
    }
}

def get_sighting_probability(animal_name: str, weather: Union[WeatherCondition, str]) -> float:
    """
    Calculates the probability of sighting a specific animal based on the
    current weather conditions at the safari camp.

    Args:
        animal_name: The name of the animal (e.g., "lion").
        weather: The current weather condition, either as a WeatherCondition
                 enum member or a string (e.g., WeatherCondition.SUNNY or "sunny").

    Returns:
        A float representing the sighting probability (0.0 to 1.0).
        Returns 0.0 if the animal is not in our database.
    """
    animal_key = animal_name.lower().strip()
    base_prob = BASE_PROBABILITIES.get(animal_key)

    if base_prob is None:
        return 0.0

    try:
        weather_condition = WeatherCondition(weather)
    except ValueError:
        # If an invalid weather string is passed, use a neutral state.
        weather_condition = None

    modifier = 0
    if weather_condition and weather_condition in WEATHER_MODIFIERS:
        modifier = WEATHER_MODIFIERS[weather_condition].get(animal_key, 0)

    final_prob = base_prob + modifier
    
    # Clamp probability between 0 and 100
    clamped_prob = max(0, min(100, final_prob))
    
    return clamped_prob / 100.0

if __name__ == '__main__':
    # Example usage
    print("Welcome to the Safari Sighting Probability Checker!")
    
    weather_today = WeatherCondition.CLOUDY
    print(f"\nCurrent weather: {weather_today.value.capitalize()}\n")

    for animal in BASE_PROBABILITIES.keys():
        probability = get_sighting_probability(animal, weather_today)
        print(f"Probability of seeing a {animal.capitalize()}: {probability:.0%}")

    print("\n--- Testing at Night ---")
    weather_night = WeatherCondition.NIGHT
    print(f"\nCurrent weather: {weather_night.value.capitalize()}\n")

    for animal in BASE_PROBABILITIES.keys():
        probability = get_sighting_probability(animal, weather_night)
        print(f"Probability of seeing a {animal.capitalize()}: {probability:.0%}")
