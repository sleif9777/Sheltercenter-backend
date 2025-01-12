import datetime
from enum import Enum
from django.db import models

class DaysOfWeek(models.IntegerChoices):
    MONDAY = 0, "Mondays"
    TUESDAY = 1, "Tuesdays"
    WEDNESDAY = 2, "Wednesdays"
    THURSDAY = 3, "Thursdays"
    FRIDAY = 4, "Fridays"
    SATURDAY = 5, "Saturdays"
    SUNDAY = 6, "Sundays"


class AppointmentTypes(models.IntegerChoices, Enum):
    ADULTS = 0, "Adults"
    PUPPIES = 1, "Puppies"
    ALL_AGES = 2, "All Ages"
    PAPERWORK = 3, "Paperwork"
    SURRENDER = 4, "Surrender"
    VISIT = 5, "Visit"
    DONATION_DROP_OFF = 6, "Donation Drop-Off"
    FUN_SIZE = 7, "Fun-Size"


class PaperworkTypes(models.IntegerChoices, Enum):
    ADOPTION = 0
    FTA = 1

class AppointmentBase(models.Model):
    weekday = models.IntegerField(choices=DaysOfWeek.choices)
    time = models.TimeField(null=False, blank=False)
    type = models.IntegerField(choices=AppointmentTypes.choices)
    # subtype = models.IntegerField(choices=PaperworkTypes.choices, null=True, blank=True)
    
    def __repr__(self):
        return "{0} at {1}".format(
            self.get_type_display(), self.print_time()
        )

    def __str__(self):
        return "{0} ({1} at {2})".format(
            self.get_type_display(), self.get_weekday_display(), self.print_time()
        )
    
    def print_time(self):
        return self.time.strftime("%-I:%M %p")
    
    @property
    def instant(self):
        return datetime.datetime(1900, 1, self.weekday + 1, self.time.hour, self.time.minute)
            
    # def get_time(self):
    #     return "TimeStringHere"
            
    # def get_weekday(self, plural=False):
    #     match self.weekday:
    #         case DaysOfWeek.MONDAY:
    #             weekday = "Monday"
    #         case DaysOfWeek.TUESDAY:
    #             weekday = "Tuesday"
    #         case DaysOfWeek.WEDNESDAY:
    #             weekday = "Wednesday"
    #         case DaysOfWeek.THURSDAY:
    #             weekday = "Thursday"
    #         case DaysOfWeek.FRIDAY:
    #             weekday = "Friday"
    #         case DaysOfWeek.SATURDAY:
    #             weekday = "Saturday"
    #         case DaysOfWeek.SUNDAY:
    #             weekday = "Sunday"
    #         case _:
    #             weekday = None
        
    #     if plural and weekday:
    #         weekday += "s"
        
    #     return weekday