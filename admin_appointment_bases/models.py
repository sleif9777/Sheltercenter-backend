from enum import Enum
from django.db import models

from appointment_bases.models import DaysOfWeek

class AdminAppointmentTypes(models.IntegerChoices, Enum):
    PAPERWORK = 3
    SURRENDER = 4
    VISIT = 5
    DONATION_DROP_OFF = 6


class PaperworkTypes(models.IntegerChoices, Enum):
    ADOPTION = 0
    FTA = 1


class AdminAppointmentBase(models.Model):
    type = models.IntegerField(choices=AdminAppointmentTypes.choices)
    subtype = models.IntegerField(choices=PaperworkTypes.choices, null=True, blank=True)
    weekday = models.IntegerField(choices=DaysOfWeek.choices)
    time = models.TimeField()

    def __repr__(self):
        if self.get_subtype():
            return "{0} ({1}) at {2}".format(
                self.get_type(), self.get_subtype(), self.get_time()
            )
        else:
            return "{0} at {2}".format(
                self.get_type(), self.get_time()
            )

    def get_type(self):
        match self.type:
            case AdminAppointmentTypes.PAPERWORK:
                return "Paperwork"
            case AdminAppointmentTypes.SURRENDER:
                return "Surrender"
            case AdminAppointmentTypes.HOST_WEEKEND_CHOSEN:
                return "Host Weekend/Chosen"
            case AdminAppointmentTypes.DONATION_DROP_OFF:
                return "Donation Drop-Off"  

    def get_subtype(self):
        match self.subtype:
            case PaperworkTypes.ADOPTION:
                return "Adoption"
            case PaperworkTypes.FTA:
                return "FTA"
            case _:
                return None
            
    def get_time(self):
        return "time string here"
    