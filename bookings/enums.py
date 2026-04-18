from enum import Enum

from django.db import models


class BookingStatus(models.IntegerChoices, Enum):
    ACTIVE = 0, "Active"
    CANCELLED = 1, "Cancelled"
    RESCHEDULED = 2, "Rescheduled"
    COMPLETED = 3, "Completed"
    NOSHOW = 4, "No Show"


class BookingMessageTemplate(models.IntegerChoices, Enum):
    LIMITED_PUPPIES = 1, "Limited Puppies"
    LIMITED_SMALL_PUPPIES = 2, "Limited Small Puppies"
    LIMITED_HYPO = 3, "Limited Hypo"
    LIMITED_FUN_SIZE = 4, "Limited Fun Size"
    DOGS_WERE_ADOPTED = 5, "Dogs Were Adopted"
    DOGS_NOT_HERE_YET = 6, "Dogs Not Here Yet"
    X_IN_QUEUE = 7, "X In Queue"
