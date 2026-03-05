from enum import Enum

from django.db import models


class EnvironmentType(models.IntegerChoices, Enum):
    PRODUCTION = 0,
    TEST = 1,
    DEVELOPMENT = 2,
    STAGING = 3