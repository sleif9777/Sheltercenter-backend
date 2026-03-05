import datetime

from appointments.mapper import AppointmentHashMapper
from django.db import models
from django.utils import timezone

from .enums import *


class AppointmentBase(models.Model):
    weekday = models.IntegerField(choices=DaysOfWeek.choices)
    time = models.TimeField(null=False, blank=False)
    type = models.IntegerField(choices=AppointmentTypes.choices)

    @property
    def instant(self):
        return timezone.make_aware(
            datetime.datetime.combine(datetime.date(1900, 1, self.weekday + 1), self.time),
            timezone.get_current_timezone(),
        )

    @property
    def time_display(self):
        return self.time.strftime("%-I:%M %p")

    def __repr__(self):
        return "{0} ({1} at {2}) [{3}]".format(
            self.get_type_display(), self.get_weekday_display(), self.print_time(), self.id
        )

    def __str__(self):
        return self.__repr__()

    def print_time(self):
        return self.time.strftime("%-I:%M %p")

    # STATIC METHODS
    @staticmethod
    def map_appointments(templates: list["AppointmentBase"]) -> list[dict]:
        return AppointmentHashMapper.map_appointments(templates)
