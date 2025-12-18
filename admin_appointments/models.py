from enum import Enum
from django.db import models

from admin_appointment_bases.models import AdminAppointmentTypes, PaperworkTypes

# Create your models here.
class AdminAppointment(models.Model):
    type = models.IntegerField(choices=AdminAppointmentTypes.choices)
    subtype = models.IntegerField(choices=PaperworkTypes.choices, null=True, blank=True)
    instant = models.DateTimeField()
    complete = models.BooleanField(default=False)

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
    