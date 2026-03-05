import datetime
import string
from typing import Union

import pytz
from django.utils import timezone


def get_today() -> datetime.date:
    return timezone.localdate()


def get_now() -> datetime.datetime:
    return timezone.now().astimezone(tz=pytz.timezone("US/Eastern"))


def get_local_instant(instant: datetime.datetime) -> datetime.datetime:
    return timezone.localtime(instant)


def get_iso_date(instant: datetime.date) -> string:
    local_dt = get_local_instant(instant)
    return local_dt.strftime("%Y-%m-%d")


def get_range_for_date(
    instant: datetime.datetime | datetime.date, backdate_days=0, forwarddate_days=0
) -> Union[datetime.datetime, datetime.datetime]:
    min_date, max_date = None, None
    eastern = pytz.timezone("US/Eastern")

    if backdate_days > 0:
        min_date = get_today() - datetime.timedelta(days=backdate_days)

    if forwarddate_days > 0:
        max_date = get_today() + datetime.timedelta(days=forwarddate_days)

    return (
        datetime.datetime.combine((min_date or instant), datetime.time.min).astimezone(tz=eastern),
        datetime.datetime.combine((max_date or instant), datetime.time.max).astimezone(tz=eastern),
    )

def is_short_notice(
        referenceDate: datetime.date, actionInstant: datetime.datetime = get_now()
    ) -> bool:
        is_same_day: bool = actionInstant.date == referenceDate

        if is_same_day:
            return True
        
        is_after_hours: bool = actionInstant.time > (
            get_closing_instant(actionInstant.date) or datetime.time(23, 59)
        )
        is_for_next_day: bool = referenceDate == get_today() + datetime.timedelta(
            days=1
        )

        return is_after_hours and is_for_next_day

def get_closing_instant(date: datetime.date) -> datetime.time:
        weekday = date.weekday

        if weekday == 6:
            return None
        elif weekday == 5:
            return datetime.time(15, 0)
        else:
            return datetime.time(18, 0)
