from enum import Enum

from django.db import models

# Let's be adults here...
class DogSex(models.IntegerChoices, Enum):
    FEMALE = 0, "Female"
    MALE = 1, "Male"

class DogStatus(models.IntegerChoices, Enum):
    AVAILABLE_NOW = 0, "Available Now"
    CHOSEN_SN = 1, "Chosen_SN"
    CHOSEN_WC = 2, "Chosen_WC"
    FTA = 3, "FTA"
    HEALTHY_IN_HOME = 4, "Healthy in Home"
    UNAVAILABLE = 5, "Unavailable",
    FOSTER = 6, "Foster"