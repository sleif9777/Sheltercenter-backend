import datetime

from adopters.models import Adopter
from appointments.models import Appointment
from django.db import models
from django.utils import timezone
from utils import DateTimeUtils

from .enums import *


# Create your models here.
class Booking(models.Model):
    adopter = models.ForeignKey(
        Adopter, null=True, blank=True, related_name="bookings", on_delete=models.PROTECT
    )
    appointment = models.ForeignKey(
        Appointment, null=True, blank=True, related_name="bookings", on_delete=models.PROTECT
    )
    status = models.IntegerField(choices=BookingStatus.choices)

    @property
    def status_display(self):
        return BookingStatus(self.status).label

    created = models.DateTimeField()

    @property
    def created_display(self):
        return DateTimeUtils.get_local_instant(self.created).strftime("%m/%d/%Y, %I:%M %p")

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
        # Adopter Name, status, instant display,
        adopter_name = self.adopter.user_profile.disambiguated_name

        name = "{0} - {1} ({2}) [{3}; APPT {4}; ADPT {5}; USER {6}]".format(
            adopter_name,
            self.appointment.instant_display,
            self.status_display,
            self.id,
            self.appointment.id,
            self.adopter.id,
            self.adopter.user_profile.id,
        )

        return name

    def __repr__(self):
        return self.__str__()

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

    @property
    def sent_template_flags(self):
        flags = []

        if self.sent_limited_puppies:
            flags.append(BookingMessageTemplate.LIMITED_PUPPIES)
        if self.sent_limited_small_puppies:
            flags.append(BookingMessageTemplate.LIMITED_SMALL_PUPPIES)
        if self.sent_limited_hypo:
            flags.append(BookingMessageTemplate.LIMITED_HYPO)
        if self.sent_limited_fun_size:
            flags.append(BookingMessageTemplate.LIMITED_FUN_SIZE)
        if self.sent_dogs_were_adopted:
            flags.append(BookingMessageTemplate.DOGS_WERE_ADOPTED)
        if self.sent_dogs_not_here_yet:
            flags.append(BookingMessageTemplate.DOGS_NOT_HERE_YET)
        if self.sent_x_in_queue:
            flags.append(BookingMessageTemplate.X_IN_QUEUE)

        return flags
