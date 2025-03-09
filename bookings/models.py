import datetime
from django.db import models
from django.utils import timezone

from adopters.models import Adopter
from appointments.models import Appointment

from .enums import *

# Create your models here.
class Booking(models.Model):
    adopter = models.ForeignKey(Adopter, null=True, blank=True, related_name='bookings', on_delete=models.PROTECT)
    appointment = models.ForeignKey(Appointment, null=True, blank=True, related_name='bookings', on_delete=models.PROTECT)
    status = models.IntegerField(choices=BookingStatus.choices)
    created = models.DateTimeField()
    modified = models.DateTimeField(null=True, blank=True)

    # MESSAGES SENT
    sent_limited_puppies = models.BooleanField(default=False)
    sent_limited_small_puppies = models.BooleanField(default=False)
    sent_limited_hypo = models.BooleanField(default=False)
    sent_limited_fun_size = models.BooleanField(default=False)
    sent_dogs_were_adopted = models.BooleanField(default=False)
    sent_dogs_not_here_yet = models.BooleanField(default=False)
    sent_x_in_queue = models.BooleanField(default=False)
    
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

    def mark_template_sent(self, template: BookingMessageTemplate):
        match template:
            case BookingMessageTemplate.LIMITED_PUPPIES:
                self.sent_limited_puppies = True
            case BookingMessageTemplate.LIMITED_SMALL_PUPPIES:
                self.sent_limited_small_puppies = True
            case BookingMessageTemplate.LIMITED_HYPO:
                self.sent_limited_hypo = True
            case BookingMessageTemplate.LIMITED_FUN_SIZE:
                self.sent_limited_fun_size = True
            case BookingMessageTemplate.DOGS_WERE_ADOPTED:
                self.sent_dogs_were_adopted = True
            case BookingMessageTemplate.DOGS_NOT_HERE_YET:
                self.sent_dogs_not_here_yet = True
            case BookingMessageTemplate.X_IN_QUEUE:
                self.sent_x_in_queue = True
            case _:
                pass
        
        self.save()
