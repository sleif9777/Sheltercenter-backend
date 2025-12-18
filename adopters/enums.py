from enum import Enum
from django.db import models

class ActivityLevelOptions(models.IntegerChoices, Enum):
    LOW = 0
    MODERATE = 1
    ACTIVE = 2
    VERY_ACTIVE = 3


class AdopterStatuses(models.IntegerChoices, Enum):
    APPROVED = 0
    PENDING = 1
    DECLINED = 2


class HomeownershipOptons(models.IntegerChoices, Enum):
    OWN = 0
    RENT = 1
    LIVE_WITH_PARENTS = 2


class HousingOptions(models.IntegerChoices, Enum):
    HOUSE = 0
    APARTMENT = 1
    CONDO = 2
    TOWNHOUSE = 3
    DORM = 4
    MOBILE_HOME = 5

class GenderPreference(models.IntegerChoices, Enum):
    MALE = 0
    FEMALE = 1
    NO_PREFERENCE = 2

class AgePreference(models.IntegerChoices, Enum):
    ADULTS = 0
    PUPPIES = 1
    NO_PREFERENCE = 2

