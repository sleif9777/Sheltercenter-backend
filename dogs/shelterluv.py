from datetime import date, datetime, timezone as dt_timezone

import requests
from django.utils import timezone

SHELTERLUV_API_ROOT = "https://new.shelterluv.com/api/v1"


def fetch_adoption_date(internal_id: str, headers: dict) -> date | None:
    """Local date of the animal's most recent Outcome.Adoption event, or None if it can't be found.

    Takes Shelterluv's Internal-ID; the per-animal endpoints 404 on the shelter-facing ID.
    """
    try:
        response = requests.get(
            f"{SHELTERLUV_API_ROOT}/animals/{internal_id}/events", headers=headers, timeout=30
        )
        if response.status_code != 200:
            return None
        times = [
            int(event["Time"])
            for event in response.json().get("events", [])
            if event.get("Type") == "Outcome.Adoption" and event.get("Time")
        ]
    except (requests.RequestException, KeyError, ValueError):
        return None

    if not times:
        return None
    return timezone.localtime(datetime.fromtimestamp(max(times), tz=dt_timezone.utc)).date()
