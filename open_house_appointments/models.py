from bookings.models import Booking
from django.db import models


# Create your models here.
class OpenHouseAppointment(models.Model):
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE)
    created_instant = models.DateTimeField()

    def __repr__(self):
        return ""