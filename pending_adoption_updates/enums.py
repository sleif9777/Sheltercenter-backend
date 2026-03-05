from enum import Enum

from django.db import models


class PendingAdoptionUpdateType(models.IntegerChoices, Enum):
    COUGH = 0, "Cough"
    NASAL_DISCHARGE = 1, "Nasal Discharge"
    OTHER = 2, "Other"