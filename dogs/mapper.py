import re
from datetime import date, datetime, timezone as dt_timezone

from .enums import DogSex, DogStatus

SHELTERLUV_STATUS_MAP = {
    "Available for Adoption": DogStatus.AVAILABLE_NOW,
    "Chosen - Needs Well Check": DogStatus.CHOSEN_WC,
    "Chosen - needs s/n": DogStatus.CHOSEN_SN,
    "Foster Care": DogStatus.UNAVAILABLE,
    "Foster Returning Soon to Farm": DogStatus.AVAILABLE_NOW,
    "Foster to Adopt for Heartworm": DogStatus.FTA,
    "Healthy In Home": DogStatus.HEALTHY_IN_HOME,
    "Hold": DogStatus.UNAVAILABLE,
    "Medical Foster": DogStatus.UNAVAILABLE,
    "Pending": DogStatus.UNAVAILABLE,
    "Deceased": DogStatus.UNAVAILABLE,
}

STATUSES_REQUIRING_UNAVAILABLE_DATE = {
    DogStatus.UNAVAILABLE,
    DogStatus.HEALTHY_IN_HOME,
    DogStatus.CHOSEN_WC,
    DogStatus.CHOSEN_SN,
    DogStatus.FTA,
}


def parse_status(animal: dict) -> DogStatus:
    raw_status = animal.get("Status", "")
    return SHELTERLUV_STATUS_MAP.get(raw_status, DogStatus.UNAVAILABLE)


def parse_timestamp(value) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromtimestamp(int(value), tz=dt_timezone.utc)
    except (ValueError, OSError):
        return None


def parse_unavailable_date(status: DogStatus, last_updated: datetime | None) -> date | None:
    if status not in STATUSES_REQUIRING_UNAVAILABLE_DATE:
        return None
    if last_updated:
        return last_updated.date()
    return date.today()


def parse_fun_size(description: str) -> bool:
    return bool(re.search(r"fridays\s*(and|&)\s*saturdays", description, re.IGNORECASE))


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

    return this_year if delta_this <= delta_next else next_year


def map_dog(animal: dict) -> dict | None:
    if animal.get("Type") != "Dog":
        return None
    try:
        description = animal.get("Description", "")
        weight_raw = animal.get("CurrentWeightPounds", "")
        status = parse_status(animal)
        last_updated = parse_timestamp(animal.get("LastUpdatedUnixTime"))
        last_intake = parse_timestamp(animal.get("LastIntakeUnixTime"))

        return {
            "shelterluv_id": int(animal["ID"]),
            "name": animal["Name"][:255],
            "description": description[:5000],
            "photo_url": animal.get("CoverPhoto", "")[:500],
            "age_months": animal.get("Age"),
            "weight": int(float(weight_raw)) if weight_raw else None,
            "sex": DogSex.MALE if animal.get("Sex") == "Male" else DogSex.FEMALE,
            "breed": animal.get("Breed", ""),
            "fun_size": parse_fun_size(description),
            "available_date": parse_available_date(description),
            "unavailable_date": parse_unavailable_date(status, last_updated),
            "last_updated": last_updated,
            "last_intake": last_intake,
            "status": status,
        }
    except (KeyError, ValueError):
        return None
