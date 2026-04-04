import datetime
from typing import Optional

from appointment_bases.enums import AppointmentTypes
from bookings.enums import BookingStatus
from django.db import models
from django.utils import timezone
from email_templates.views import EmailViewSet

from .enums import OutcomeTypes, AppointmentCategories


# Create your models here.
class Appointment(models.Model):
    # APPOINTMENT TYPE
    type = models.IntegerField(choices=AppointmentTypes.choices)

    @property
    def type_display(self):
        return AppointmentTypes(self.type).label.upper()

    @property
    def is_adoption_appointment(self):
        return self.type_category == AppointmentCategories.ADOPTION

    @property
    def is_admin_appointment(self):
        return self.type_category == AppointmentCategories.ADMIN

    @property
    def is_surrender_appointment(self):
        return self.type == AppointmentTypes.SURRENDER

    @property
    def is_paperwork_appointment(self):
        return self.type == AppointmentTypes.PAPERWORK

    @property
    def is_donation_dropoff(self):
        return self.type == AppointmentTypes.DONATION_DROP_OFF

    @property
    def type_category(self) -> AppointmentCategories:
        match self.type:
            case (
                AppointmentTypes.ADULTS
                | AppointmentTypes.ALL_AGES
                | AppointmentTypes.FUN_SIZE
                | AppointmentTypes.PUPPIES
            ):
                return AppointmentCategories.ADOPTION

            case (
                AppointmentTypes.PAPERWORK
                | AppointmentTypes.VISIT
                | AppointmentTypes.SURRENDER
                | AppointmentTypes.DONATION_DROP_OFF
            ):
                return AppointmentCategories.ADMIN

    # APPOINTMENT INSTANT AND RELATED PROPERTIES
    instant = models.DateTimeField()  # No client support

    @property
    def local_dt(self): 
        return timezone.localtime(self.instant)

    @property
    def iso_date(self):
        return self.local_dt.strftime("%Y-%m-%d")

    @property
    def iso_instant(self):
        return self.local_dt.strftime("%Y-%m-%dT%H:%M:%SZ")

    @property
    def weekday(self):
        return self.local_dt.weekday()

    @property
    def instant_display(self):
        return self.local_dt.strftime("%b %d, %I:%M %p")

    @property
    def time_display(self):
        return self.local_dt.strftime("%I:%M %p")

    # DESCRIPTORS
    @property
    def description(self):
        if self.is_adoption_appointment:
            booking = self.get_current_booking()
            return booking.adopter.user_profile.full_name if booking is not None else "OPEN"

        if self.is_paperwork_appointment:
            return self.appointment_notes or "UNKNOWN"

        if self.is_surrender_appointment:
            dogDisplay = self.surrendered_dog or "UNKNOWN"

            if self.is_surrender_appointment and self.surrendered_dog_fka:
                dogDisplay += " (fka {0})".format(self.surrendered_dog_fka)

            return dogDisplay

        if self.is_donation_dropoff:
            return "DONATION DROP-OFF"

        return self.appointment_notes

    # ADMINISTRATIVE FIELDS
    locked = models.BooleanField(default=False)
    soft_deleted = models.BooleanField(default=False)
    appointment_notes = models.CharField(default="", max_length=1000, null=True, blank=True)

    @property
    def has_current_booking(self):
        return self.get_current_booking() is not None

    # CHECK-IN FIELDS
    check_in_time = models.DateTimeField(null=True, blank=True)

    @property
    def is_checked_in(self):
        return (
            self.is_adoption_appointment
            and self.check_in_time is not None
            and self.check_out_time is None
        )

    @property
    def check_in_time_display(self):
        if self.check_in_time is None:
            return ""
        
        local_dt = timezone.localtime(self.check_in_time)
        return local_dt.strftime("%I:%M %p")

    # CHECK-OUT FIELDS
    check_out_time = models.DateTimeField(null=True, blank=True)

    @property
    def is_checked_out(self):
        return self.is_adoption_appointment and self.check_out_time is not None

    @property
    def check_out_time_display(self):
        if self.check_out_time is None:
            return ""
        
        local_dt = timezone.localtime(self.check_out_time)
        return local_dt.strftime("%I:%M %p")

    @property
    def is_no_show(self):
        return self.outcome == OutcomeTypes.NO_SHOW

    clothing_description = models.CharField(default="", max_length=1000, null=True, blank=True)
    counselor = models.CharField(default="", max_length=100, null=True, blank=True)

    # OUTCOME FIELDS
    outcome = models.IntegerField(choices=OutcomeTypes, null=True, blank=True)

    @property
    def outcome_value_display(self):
        if self.outcome is None:
            return ""

        outcome = OutcomeTypes(self.outcome).label.upper()

        if self.has_adoption_outcome:
            outcome += ": {0}".format(self.chosen_dog)
        
        return outcome

    @property
    def has_adoption_outcome(self):
        return self.outcome in [OutcomeTypes.ADOPTION, OutcomeTypes.CHOSEN, OutcomeTypes.FTA]

    chosen_dog = models.CharField(default="", max_length=1000, null=True, blank=True)

    # SURRENDER FIELDS
    surrendered_dog = models.CharField(default="", max_length=1000, null=True, blank=True)
    surrendered_dog_fka = models.CharField(default="", max_length=1000, null=True, blank=True)

    # OTHER RELATIONAL FIELDS
    def __repr__(self):
        return str(self)

    def __str__(self):
        desc = self.description

        if desc == "OPEN":
            desc += " ({0})".format(self.type_display)

        if self.outcome is not None:
            return "{0} - {1} ({2}) [{3}]".format(
                desc, self.instant_display, self.outcome_value_display, self.id
            )

        id_display = "{0}".format(self.id)
        id_display += " - SOFT DELETED" if self.soft_deleted else ""

        return "{0} - {1} [{2}]".format(desc, self.instant_display, id_display)

    # ADMINISTRATIVE METHODS
    def check_in(self, request_data):
        clothing: Optional[str] = request_data.get("clothingDescription", "")
        counselor: Optional[str] = request_data.get("counselor", "")
        
        if self.check_in_time is None:
            self.check_in_time = timezone.now()

        self.clothing_description = clothing
        self.counselor = counselor
        self.save()

    def check_out(self, outcome: OutcomeTypes, dog: Optional[str]):
        # Process on the appointment level
        self.check_out_time = timezone.now()
        self.outcome = outcome
        self.chosen_dog = dog
        self.save()

        # Then the booking itself
        booking = self.get_current_booking()
        booking.mark_status(BookingStatus.COMPLETED)

    def get_current_booking(self) -> Optional["Booking"]:  # type: ignore
        for booking in self.bookings.all():
            if booking.status in [
                BookingStatus.ACTIVE,
                BookingStatus.NOSHOW,
                BookingStatus.COMPLETED,
            ]:
                return booking

        return None

    def no_show(self):
        self.outcome = OutcomeTypes.NO_SHOW
        self.save()

        booking = self.get_current_booking()
        booking.mark_status(BookingStatus.NOSHOW)

        EmailViewSet().NoShow(self)

    def soft_delete(self):
        self.soft_deleted = True
        self.save()

    def toggle_lock(self, override: Optional[bool] = None):
        self.locked = override if override is not None else not self.locked
        self.save()

    # STATIC METHODS
    @staticmethod
    def get_appts_missing_outcomes() -> list["Appointment"]:
        initial_query = Appointment.objects.filter(
            instant__lt=datetime.datetime.combine(datetime.datetime.today(), datetime.time.min),
            outcome=None,
            type__lt=AppointmentTypes.PAPERWORK,
        )

        # Filter out those without bookings
        return [appt for appt in initial_query if appt.get_current_booking()]
