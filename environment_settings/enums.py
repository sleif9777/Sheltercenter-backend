from django.db import models
from enum import Enum

class EnvironmentType(models.IntegerChoices, Enum):
    PRODUCTION = 0,
    TEST = 1,
    DEVELOPMENT = 2,
    STAGING = 3