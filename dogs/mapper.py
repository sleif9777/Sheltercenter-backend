import re
from datetime import date

from .enums import DogSex


def parse_fun_size(description: str) -> bool:
    return bool(re.search(r"fridays and saturdays", description, re.IGNORECASE))


def parse_available_date(description: str) -> date | None:
    match = re.search(r"\*\*.*?(\d{1,2}/\d{1,2}).*?\*\*", description)
    if not match:
        return None

    month, day = map(int, match.group(1).split("/"))
    today = date.today()

    this_year = date(today.year, month, day)
    next_year = date(today.year + 1, month, day)

    delta_this = abs((this_year - today).days)
    delta_next = abs((next_year - today).days)

    # In case of tie, prefer future (next_year)
    return this_year if delta_this <= delta_next else next_year


def map_dog(animal: dict) -> dict | None:
    try:
        description = animal.get("Description", "")
        weight_raw = animal.get("CurrentWeightPounds", "")

        return {
            "shelterluv_id": int(animal["ID"]),
            "name": animal["Name"],
            "description": description,
            "photo_url": animal.get("CoverPhoto", ""),
            "age_months": animal.get("Age"),
            "weight": int(float(weight_raw)) if weight_raw else None,
            "sex": DogSex.MALE if animal.get("Sex") == "Male" else DogSex.FEMALE,
            "breed": animal.get("Breed", ""),
            "fun_size": parse_fun_size(description),
            "available_date": parse_available_date(description),
            "available_now": True,
            "unavailable_date": None,
        }
    except (KeyError, ValueError) as e:
        return None
