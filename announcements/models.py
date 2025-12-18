from enum import Enum
from django.db import models

class AnnouncementTypes(models.IntegerChoices, Enum):
    DAILY = 0
    INTERNAL = 1
    STATIC = 2


# Create your models here.
class Announcement(models.Model):
    type = models.IntegerField(choices=AnnouncementTypes.choices)
    content = models.CharField(default="", max_length=1000)
    date = models.DateField()

    def __repr__(self):
        return ""