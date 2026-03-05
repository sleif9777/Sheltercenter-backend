from enum import Enum

from django.db import models


class BookingStatus(models.IntegerChoices, Enum):
    ACTIVE = 0, "Active"
    CANCELLED = 1, "Cancelled"
    RESCHEDULED = 2, "Rescheduled"
    COMPLETED = 3, "Completed"
    NOSHOW = 4, "No Show"


class BookingMessageTemplate(models.IntegerChoices, Enum):
    LIMITED_PUPPIES = 0, "Limited Puppies"
    LIMITED_SMALL_PUPPIES = 1, "Limited Small Puppies"
    LIMITED_HYPO = 2, "Limited Hypo"
    LIMITED_FUN_SIZE = 3, "Limited Fun Size"
    DOGS_WERE_ADOPTED = 4, "Dogs Were Adopted"
    DOGS_NOT_HERE_YET = 5, "Dogs Not Here Yet"
    X_IN_QUEUE = 6, "X In Queue"
