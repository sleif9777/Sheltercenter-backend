import datetime
import pytz
import string

from django.utils import timezone
from typing import Union
from zoneinfo import ZoneInfo

class DateTimeUtils:
    @staticmethod
    def GetToday() -> datetime.date:
        return timezone.now().date()
    
    @staticmethod
    def GetNow() -> datetime.datetime:
        return timezone.now()
    
    @staticmethod
    def IsShortNotice(referenceInstant: datetime.datetime, actionInstant: datetime.datetime=GetNow()) -> bool:
        isSameDay: bool = actionInstant.date == referenceInstant.date()
        isAfterHours: bool = actionInstant.time > (DateTimeUtils.GetClosingInstant(actionInstant) or datetime.time(23, 59))
        isForNextDay: bool = referenceInstant.date == DateTimeUtils.GetToday() + datetime.timedelta(days=1)

        return isSameDay or (isAfterHours and isForNextDay)
    
    @staticmethod
    def GetClosingInstant(date: datetime.datetime) -> datetime.time:
        weekday = date.weekday

        if weekday == 6:
            return None
        elif weekday == 5:
            return datetime.time(15,0)
        else:
            return datetime.time(18,0)
        
    @staticmethod
    def Parse(instant: string, format: string, isUTC=False) -> datetime.datetime:
        match format:
            case "MM/DD/YYYY":
                return datetime.datetime.strptime(instant, "%m/%d/%Y")
            case "JSON":
                parsed_date = datetime.datetime.strptime(instant, "%Y-%m-%dT%H:%M:%S.%fZ")

                return datetime.datetime \
                    .strptime(instant, "%Y-%m-%dT%H:%M:%S.%fZ") \
                    .replace(tzinfo=pytz.utc) \
                    .astimezone(tz=None)
            case _:
                return
            
    @staticmethod
    def GetRangeForDate(instant: datetime.datetime, backdateDays=0, forwarddateDays=0) -> Union[datetime.datetime, datetime.datetime]:
        minDate, maxDate = None, None

        if backdateDays > 0:
            minDate = DateTimeUtils.GetToday() - datetime.timedelta(days=backdateDays)
        
        if forwarddateDays > 0:
            maxDate = DateTimeUtils.GetToday() + datetime.timedelta(days=forwarddateDays)

        return (datetime.datetime.combine((minDate or instant), datetime.time.min),
                datetime.datetime.combine((maxDate or instant), datetime.time.max))
    
    @staticmethod
    def GetMinForDate(date: datetime.datetime) -> datetime.datetime:
        return datetime.datetime.combine(date, datetime.time.min)