from django.db import models
from enum import Enum

class SecurityLevels(models.IntegerChoices, Enum):
    ADOPTER = 0
    GREETER = 1
    ADMIN = 2,
    SUPERUSER = 3,