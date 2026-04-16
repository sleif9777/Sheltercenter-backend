from __future__ import annotations
import datetime

from appointments.enums import OutcomeTypes
from bookings.enums import BookingStatus
from django.core.exceptions import ObjectDoesNotExist
from django.utils import timezone
from utils import DateTimeUtils

from .enums import *


# Create your models here.
class Adopter(models.Model):
    # USER PROFILE ITEMS
    primary_email = models.EmailField(
        default="", max_length=100, null=False, blank=False, unique=True
    )

    status = models.IntegerField(choices=ApprovalStatus.choices)

    @property
    def status_display(self):
        return ApprovalStatus(self.status).label

    @property
    def is_approved(self):
        return self.status == ApprovalStatus.APPROVED

    # APPLICATION ITEMS
    shelterluv_app_id = models.CharField(default="", max_length=50, null=True, blank=True)
    shelterluv_id = models.CharField(default="", max_length=50, null=True, blank=True)
    approval_emailed = models.BooleanField(default=False)

    approved_until = models.DateField(null=False, blank=False)

    @property
    def approved_until_iso(self):  # TODO: deprecate and send date in ISO to server
        return self.approved_until.isoformat()

    @property
    def approval_expired(self):
        return self.approved_until < DateTimeUtils.get_today()

    # UPLOAD ITEMS
    last_uploaded = models.DateTimeField(null=True, blank=True)

    @property
    def last_uploaded_display(self):
        if not self.last_uploaded:
            return None

        local_dt = timezone.localtime(self.last_uploaded)
        return local_dt.strftime("%a %b %d, %I:%M %p")

    @property
    def should_send_approval_email(self):
        if not self.is_approved:
            return False

        never_uploaded = self.last_uploaded is None

        if never_uploaded:
            return True

        two_days_ago = timezone.now() - datetime.timedelta(hours=48)
        is_old_enough = self.last_uploaded < two_days_ago

        return is_old_enough

    # HOUSING ENVIRONMENT ITEMS
    homeowner = models.IntegerField(choices=HomeownershipOptons.choices, null=True, blank=True)
    housing_type = models.IntegerField(choices=HousingOptions.choices, null=True, blank=True)
    activity_level = models.IntegerField(
        choices=ActivityLevelOptions.choices, null=True, blank=True
    )
    has_fence = models.BooleanField(default=False)
    dogs_in_home = models.BooleanField(default=False)
    cats_in_home = models.BooleanField(default=False)
    other_pets_in_home = models.BooleanField(default=False)
    other_pets_comment = models.CharField(default="", max_length=100, null=True, blank=True)

    # NOTES ITEMS
    application_comments = models.CharField(default="", max_length=1000, null=True, blank=True)
    internal_notes = models.CharField(default="", max_length=500, null=True, blank=True)
    adopter_notes = models.CharField(default="", max_length=500, null=True, blank=True)

    # ADOPTER PREFERENCE ITEMS
    gender_preference = models.IntegerField(choices=GenderPreference.choices, null=True, blank=True)

    @property
    def gender_preference_display(self):
        return (
            GenderPreference(self.gender_preference).label
            if self.gender_preference
            else "No Preference"
        )

    age_preference = models.IntegerField(choices=AgePreference.choices, null=True, blank=True)

    @property
    def age_preference_display(self):
        return AgePreference(self.age_preference).label if self.age_preference else "No Preference"

    min_weight_preference = models.IntegerField(null=True, blank=True)
    max_weight_preference = models.IntegerField(null=True, blank=True)
    low_allergy = models.BooleanField(default=False)

    # VISIT LOGISTICS ITEMS
    mobility = models.BooleanField(default=False)
    bringing_dog = models.BooleanField(default=False)

    @property
    def lives_with_parents(self):
        return self.homeowner == HomeownershipOptons.LIVE_WITH_PARENTS

    # BOOKING HISTORY ITEMS
    @property
    def has_current_booking(self):
        return self.bookings.filter(status=BookingStatus.ACTIVE).count() > 0

    @property
    def last_booking_activity(self):
        recent_booking = self.bookings.order_by("-modified").first()

        if recent_booking:
            return (
                recent_booking.modified
                if recent_booking.modified is not None
                else recent_booking.created
            )

        return None

    @property
    def booking_history(self):
        bookings = self.bookings
        completed = bookings.filter(status=BookingStatus.COMPLETED)
        no_show = bookings.filter(status=BookingStatus.NOSHOW)
        no_decision = [b for b in completed if b.appointment.outcome == OutcomeTypes.NO_DECISION]
        adopted = [b for b in completed if b.appointment.has_adoption_outcome]

        return {
            "completed": completed.count(),
            "noShow": no_show.count(),
            "noDecision": len(no_decision),
            "adopted": len(adopted),
        }

    # OTHER RELATIONAL FIELDS
    def __repr__(self):
        return self.user_profile.disambiguated_name

    def __str__(self):
        return "{0} [{1}]".format(self.user_profile.disambiguated_name, self.id)

    # RELATIONAL METHODS
    def get_current_appointment(self) -> Appointment | None:  # type: ignore
        try:
            return self.bookings.get(status=BookingStatus.ACTIVE).appointment
        except:
            return None

    def should_email_watchlist_updates(self) -> bool:
        current_appt = self.get_current_appointment()
        today = DateTimeUtils.get_today()

        if not current_appt:
            return False

        appt_date: datetime.date = current_appt.instant.date()

        if appt_date < today:
            return False

        if appt_date() == today:
            return (
                # Only consider same-day appointments as "in the future" 
                # if they haven't been checked in yet, to avoid sending 
                # irrelevant notifications to adopters who have already 
                # come in for their appointment
                not current_appt.is_checked_in 
                and not current_appt.is_checked_out
                and not current_appt.is_no_show
            )

        return True

    def get_flags(self) -> str:
        flags = []

        if self.booking_history["noShow"] > 1:
            flags.append("{0} no shows".format(self.booking_history["noShow"]))

        if self.booking_history["noDecision"] > 1:
            flags.append("{0} no decision".format(self.booking_history["noDecision"]))

        return ", ".join(flags)

    # ADMINISTRATIVE METHODS
    def restrict_calendar(self, restrict=True):
        self.user_profile.adoption_completed = restrict
        self.user_profile.save()

    def update_preferences(self, data):
        self.homeowner = data.get("housingOwnership")
        self.housing_type = data.get("housingType")
        self.gender_preference = data.get("genderPreference")
        self.age_preference = data.get("agePreference")
        self.activity_level = data.get("activityLevel")

        self.dogs_in_home = data.get("hasDogs", False)
        self.cats_in_home = data.get("hasCats", False)
        self.other_pets_in_home = data.get("hasOtherPets", False)

        self.other_pets_comment = data.get("otherPetsComment", "")
        self.has_fence = data.get("hasFence", False)
        self.bringing_dog = data.get("bringingDog", False)
        self.low_allergy = data.get("lowShed", False)
        self.mobility = data.get("mobility", False)

        self.min_weight_preference = data.get("minWeightPreference")
        self.max_weight_preference = data.get("maxWeightPreference")

        self.internal_notes = data.get("internalNotes", "")
        self.adopter_notes = data.get("adopterNotes", "")

        self.save()

    def update_from_shelterluv_import(self, data):
        self.status = data["status"]
        self.shelterluv_id = data["shelterluv_id"]
        self.approved_until = self.get_default_approval_date()
        self.save()

    def update_last_upload(self):
        self.last_uploaded = timezone.now()
        self.save()

    def update_address(self, request_data):
        street_address = request_data.get("streetAddress", "")
        city = request_data.get("city", "")
        state = request_data.get("state", "")
        postal_code = request_data.get("postalCode", "")
        user = self.user_profile

        user.street_address = street_address
        user.city = city
        user.state = state
        user.postal_code = postal_code
        user.save()

    # STATIC METHODS
    @staticmethod
    def get_application_status(
        status: str | int, get_from=str | None
    ) -> tuple[ApprovalStatus, bool]:
        # Returns
        #   1. New status
        #   2. Whether we avoided approving a previously-blocked adopter
        if get_from:
            try:
                adopter = Adopter.objects.get(primary_email=get_from)

                # DON'T SWITCH PREVIOUS BLOCKS TO APPROVED VIA JOB - SHOULD BE MANUAL AND DELIBERATE
                if adopter.status == ApprovalStatus.DECLINED:
                    return adopter.status, True
            except ObjectDoesNotExist:
                pass

        match status:
            case "Accepted" | 0:
                return_status = ApprovalStatus.APPROVED
            case "Denied" | 2:
                return_status = ApprovalStatus.DECLINED
            case "Pending" | "Archived" | 1 | _:
                return_status = ApprovalStatus.PENDING

        return return_status, False

    @staticmethod
    def get_default_approval_date() -> datetime.date:
        year = timezone.now().year + 1
        return timezone.now().replace(year=year).date()

    # CLASS METADATA
    class Meta:
        ordering = ["user_profile", "primary_email"]
