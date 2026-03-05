from enum import Enum

from django.db import models


class AppointmentCategories(models.IntegerChoices):
    ADOPTION = 0, "Adoption"
    ADMIN = 1, "Admin"


class OutcomeTypes(models.IntegerChoices, Enum):
    ADOPTION = 0
    FTA = 1
    CHOSEN = 2
    NO_DECISION = 3
    NO_SHOW = 4
