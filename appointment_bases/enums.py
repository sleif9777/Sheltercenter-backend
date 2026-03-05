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
    ALL_AGES = 2, "All Ages and Sizes"
    PAPERWORK = 3, "Paperwork"
    SURRENDER = 4, "Surrender"
    VISIT = 5, "Visit"
    DONATION_DROP_OFF = 6, "Donation Drop-Off"
    FUN_SIZE = 7, "Fun-Size"


class PaperworkTypes(models.IntegerChoices, Enum):
    ADOPTION = 0
    FTA = 1
