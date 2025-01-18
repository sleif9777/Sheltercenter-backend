import datetime
from django.db import models
from django.utils import timezone

from adopters.models import Adopter
from appointments.models import Appointment

from .enums import BookingStatus

# Create your models here.
class Booking(models.Model):
    adopter = models.ForeignKey(Adopter, null=True, blank=True, related_name='bookings', on_delete=models.PROTECT)
    appointment = models.ForeignKey(Appointment, null=True, blank=True, related_name='bookings', on_delete=models.PROTECT)
    status = models.IntegerField(choices=BookingStatus.choices)
    created = models.DateTimeField()
    modified = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return str(self.appointment.id) + str(self.status) + self.adopter.user_profile.disambiguated_name

    def __repr__(self):
        return str(self.appointment.id) + str(self.status) + self.adopter.user_profile.disambiguated_name
    
    @property
    def previous_visits(self):
        return Booking.objects.filter(
            adopter=self.adopter,
            status=BookingStatus.COMPLETED
        ).count()
    
    def mark_status(self, status: BookingStatus):
        self.status = status
        self.modified = timezone.now()
        self.save()
