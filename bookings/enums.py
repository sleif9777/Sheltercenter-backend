from enum import Enum
from django.db import models

class BookingStatus(models.IntegerChoices, Enum):
    ACTIVE = 0
    CANCELLED = 1
    RESCHEDULED = 2
    COMPLETED = 3
    NOSHOW = 4

class BookingMessageTemplate(models.IntegerChoices, Enum):
    LIMITED_PUPPIES = 0
    LIMITED_SMALL_PUPPIES = 1
    LIMITED_HYPO = 2
    LIMITED_FUN_SIZE = 3
    DOGS_WERE_ADOPTED = 4
    DOGS_NOT_HERE_YET = 5
    X_IN_QUEUE = 6