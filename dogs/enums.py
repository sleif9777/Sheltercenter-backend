from enum import Enum

from django.db import models

# Let's be adults here...
class DogSex(models.IntegerChoices, Enum):
    FEMALE = 0, "Female"
    MALE = 1, "Male"