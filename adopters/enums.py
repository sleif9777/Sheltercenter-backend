from enum import Enum

from django.db import models


class ActivityLevelOptions(models.IntegerChoices, Enum):
    LOW = 0, "Low"
    MODERATE = 1, "Moderate"
    ACTIVE = 2, "Active"
    VERY_ACTIVE = 3, "Very Active"


class ApprovalStatus(models.IntegerChoices, Enum):
    APPROVED = 0, "Approved"
    PENDING = 1, "Pending"
    DECLINED = 2, "Declined"


class HomeownershipOptons(models.IntegerChoices, Enum):
    OWN = 0, "Own"
    RENT = 1, "Rent"
    LIVE_WITH_PARENTS = 2, "Live with Parents"


class HousingOptions(models.IntegerChoices, Enum):
    HOUSE = 0, "House"
    APARTMENT = 1, "Apartment"
    CONDO = 2, "Condo"
    TOWNHOUSE = 3, "Townhouse"
    DORM = 4, "Dorm"
    MOBILE_HOME = 5, "Mobile Home"

class GenderPreference(models.IntegerChoices, Enum):
    MALE = 0, "Males"
    FEMALE = 1, "Females"
    NO_PREFERENCE = 2, "No Preference"

class AgePreference(models.IntegerChoices, Enum):
    ADULTS = 0, "Adults"
    PUPPIES = 1, "Puppies"
    NO_PREFERENCE = 2, "No Preference"

