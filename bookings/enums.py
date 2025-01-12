from enum import Enum
from django.db import models

class BookingStatus(models.IntegerChoices, Enum):
    ACTIVE = 0
    CANCELLED = 1
    RESCHEDULED = 2
    COMPLETED = 3
    NOSHOW = 4