import datetime
from django.db import models
from django.utils import timezone

from appointment_bases.models import AppointmentTypes
from email_templates.views import EmailViewSet
from utils import DateTimeUtils
from bookings.enums import BookingStatus

from .enums import OutcomeTypes

# Create your models here.
class Appointment(models.Model):
    type = models.IntegerField(choices=AppointmentTypes.choices)
    instant = models.DateTimeField()
    locked = models.BooleanField(default=False)
    soft_deleted = models.BooleanField(default=False)

    check_in_time = models.DateTimeField(null=True, blank=True)
    check_out_time = models.DateTimeField(null=True, blank=True)
    clothing_description = models.CharField(default="", max_length=1000, null=True, blank=True)
    counselor = models.CharField(default="", max_length=100, null=True, blank=True)  
    appointment_notes = models.CharField(default="", max_length=1000, null=True, blank=True)  
    outcome = models.IntegerField(choices=OutcomeTypes, null=True, blank=True)

    # SURRENDER ONLY FIELDS
    surrendered_dog = models.CharField(default="", max_length=1000, null=True, blank=True)
    surrendered_dog_fka = models.CharField(default="", max_length=1000, null=True, blank=True)

    def __repr__(self):
        return "{0} at {1}".format(
            datetime.datetime.strftime(self.instant, "%b %d, %Y"),
            datetime.datetime.strftime(self.instant, "%h:%M %A"),
        )
    
    def __str__(self):
        return "{0} at {1}".format(
            self.type,
            datetime.datetime.strftime(self.instant, "%-H:%M %p (%b %d, %Y)"),
        )
    
    def get_time_string(self):
        return "{0} at {1}".format(
            datetime.datetime.strftime(self.instant, "%b %d, %Y"),
            datetime.datetime.strftime(self.instant, "%-H:%M %p"),
        )
    
    def toggle_lock(self, override: bool|None=None):
        self.locked = override if override else not self.locked
        self.save()

    def soft_delete(self):
        self.soft_deleted = True
        self.save()

    def get_current_booking(self):
        for booking in self.bookings.all():
            if booking.status in [
                    BookingStatus.ACTIVE, 
                    BookingStatus.NOSHOW, 
                    BookingStatus.COMPLETED
                ]:
                return booking
            
        return None
    
    def check_in(self, clothing, counselor):
        self.check_in_time = timezone.now()
        self.clothing_description = clothing
        self.counselor = counselor
        self.save()

    def check_out(self, outcome):
        # Process on the appointment level
        self.check_out_time = timezone.now()
        self.outcome = outcome
        self.save()
        
        # Then the booking itself
        booking = self.get_current_booking()
        booking.mark_status(BookingStatus.COMPLETED)

    def no_show(self):
        self.outcome = OutcomeTypes.NO_SHOW
        self.save()

        booking = self.get_current_booking()
        booking.mark_status(BookingStatus.NOSHOW)

        EmailViewSet().NoShow(self)

    @staticmethod
    def get_appts_missing_outcomes():
        initial_query = Appointment.objects.filter(
            instant__lt=datetime.datetime.combine(datetime.datetime.today(), datetime.time.min),
            outcome=None,
            type__lt=AppointmentTypes.PAPERWORK,
        )

        #Filter out those without bookings
        return [appt for appt in initial_query if appt.get_current_booking()]