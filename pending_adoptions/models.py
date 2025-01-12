from enum import Enum
from django.db import models

from admin_appointments.models import AdminAppointment
from adopters.models import Adopter
from appointments.models import Appointment

from .enums import CircumstanceOptions, PendingAdoptionStatus

class PendingAdoption(models.Model):
    created_instant = models.DateTimeField(auto_now_add=True)
    circumstance = models.IntegerField(choices=CircumstanceOptions.choices)
    dog = models.CharField(default="", max_length=50)
    adopter = models.ForeignKey(Adopter, on_delete=models.CASCADE)
    source_appointment = models.OneToOneField(
        Appointment, 
        null=True, 
        blank=True, 
        on_delete=models.PROTECT,
        related_name="source_adoption"
    )
    paperwork_appointment = models.OneToOneField(
        Appointment, 
        null=True, 
        blank=True, 
        on_delete=models.PROTECT,
        related_name="paperwork_adoption"
    )
    status = models.IntegerField(choices=PendingAdoptionStatus.choices)
    ready_to_roll_instant = models.DateTimeField(null=True, blank=True)
    heartworm_positive = models.BooleanField(default=False)

    def mark_status(self, new_status, heartworm):
        self.status = new_status
        self.heartworm_positive = heartworm
        self.save()
