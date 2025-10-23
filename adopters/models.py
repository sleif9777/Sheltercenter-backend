import datetime

from django.core.exceptions import ObjectDoesNotExist
from django.utils import timezone

from appointments.enums import OutcomeTypes
from bookings.enums import BookingStatus

from .enums import *

# Create your models here.
class Adopter(models.Model):
    # USER PROFILE ITEMS
    primary_email = models.EmailField(default="", max_length=100, null=False, blank=False, unique=True)
    status = models.IntegerField(choices=AdopterStatuses.choices)

    # APPLICATION ITEMS
    shelterluv_app_id = models.CharField(default="", max_length=50, null=True, blank=True)
    shelterluv_id = models.CharField(default="", max_length=50, null=True, blank=True)
    approved_until = models.DateField(null=False, blank=False)
    last_uploaded = models.DateTimeField(null=True, blank=True)
    approval_emailed = models.BooleanField(default=False)

    # HOUSING ENVIRONMENT ITEMS
    homeowner = models.IntegerField(choices=HomeownershipOptons.choices, null=True, blank=True)
    housing_type = models.IntegerField(choices=HousingOptions.choices, null=True, blank=True)
    activity_level = models.IntegerField(choices=ActivityLevelOptions.choices, null=True, blank=True)
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
    age_preference = models.IntegerField(choices=AgePreference.choices, null=True, blank=True)
    min_weight_preference = models.IntegerField(null=True, blank=True)
    max_weight_preference = models.IntegerField(null=True, blank=True)
    low_allergy = models.BooleanField(default=False)

    # VISIT LOGISTICS ITEMS
    mobility = models.BooleanField(default=False)
    bringing_dog = models.BooleanField(default=False)

    @property
    def lives_with_parents(self):
        return self.homeowner == HomeownershipOptons.LIVE_WITH_PARENTS
    
    @property
    def has_current_booking(self):
        return self.bookings.filter(status=BookingStatus.ACTIVE).count() > 0
    
    @property
    def last_booking_activity(self):
        recent_booking = self.bookings.order_by('-modified').first()
        
        if recent_booking:
            return recent_booking.modified if recent_booking.modified is not None else recent_booking.created
        
        return None
    
    @property
    def booking_history(self):
        # TODO: flesh this out, and compute the outcome of completed appointments
        bookings = self.bookings
        completed = bookings.filter(status=BookingStatus.COMPLETED)
        no_show = bookings.filter(status=BookingStatus.NOSHOW)
        no_decision = [b for b in completed if b.appointment.outcome == OutcomeTypes.NO_DECISION]
        adopted = [b for b in completed 
                   if b.appointment.outcome in [
                       OutcomeTypes.ADOPTION, OutcomeTypes.CHOSEN, OutcomeTypes.FTA
                   ]]

        return {
            "completed": completed.count(),
            "noShow": no_show.count(),
            "noDecision": len(no_decision),
            "adopted": len(adopted)
        }
    
    class Meta:
        ordering = ["user_profile", "primary_email"]
    
    def get_current_appointment(self):
        try:
            return self.bookings.get(status=BookingStatus.ACTIVE).appointment
        except:
            return None
        
    def get_flags(self):
        flags = []

        if self.booking_history['noShow'] > 1:
            flags.append("{0} no shows".format(self.booking_history['noShow']))
        
        if self.booking_history['noDecision'] > 1:
            flags.append("{0} no decision".format(self.booking_history['noDecision']))

        return ", ".join(flags)

    def send_approval_email(self):
        return self.status == AdopterStatuses.APPROVED and self.recently_uploaded()
    
    def recently_uploaded(self):
        never_uploaded = self.last_uploaded is None

        if never_uploaded:
            not_uploaded_last_48_hours = False
        else:
            two_days_ago = timezone.now() - datetime.timedelta(hours=48)
            not_uploaded_last_48_hours = self.last_uploaded < two_days_ago

        return never_uploaded or not_uploaded_last_48_hours

    def __repr__(self):
        return self.user_profile.disambiguated_name
    
    def __str__(self):
        return self.user_profile.disambiguated_name
    
    def update_from_shelterluv_import(self, data):
        self.status = data['status']
        self.shelterluv_id = data['shelterluv_id']
        self.approved_until = self.get_default_approval_date()
        self.save()

    def restrict_calendar(self, restrict=True):
        self.user_profile.adoption_completed = restrict
        self.user_profile.save()

    @staticmethod
    def get_default_approval_date():
        year = datetime.datetime.today().year + 1
        return datetime.datetime.today().replace(year=year).date()
    
    @staticmethod
    def get_application_status(status, get_from=None):
        # Returns
        #   1. New status
        #   2. Whether we avoided approving a previously-blocked adopter
        match status:
            case "Accepted" | 0:
                return_status = AdopterStatuses.APPROVED
            case "Denied" | 2:
                return_status = AdopterStatuses.DECLINED
            case "Pending" | "Archived" | 1 | _:
                return_status = AdopterStatuses.PENDING
            
        if get_from:
            try:
                adopter = Adopter.objects.get(primary_email=get_from)

                # DON'T SWITCH PREVIOUS BLOCKS TO DECLINED VIA JOB - SHOULD BE MANUAL AND DELIBERATE
                if adopter.status == AdopterStatuses.DECLINED:
                    return adopter.status, True
            except ObjectDoesNotExist:
                pass
        
        return return_status, False

    ### Booking logic ###
    def update_from_booking(self, data):
        self.homeowner = data['housingOwnership'] or None
        self.housing_type = data['housingType'] or None
        self.activity_level = data['activityLevel'] or None
        self.has_fence = data['hasFence']
        self.dogs_in_home = data['hasDogs']
        self.cats_in_home = data['hasCats']
        self.other_pets_in_home = data['hasOtherPets']
        self.other_pets_comment = data['otherPetsComment']

        self.adopter_notes = data['adopterNotes']
        self.internal_notes = data['internalNotes']

        self.gender_preference = data['genderPreference']
        self.age_preference = data['agePreference']
        self.min_weight_preference = data['minWeightPreference']
        self.max_weight_preference = data['maxWeightPreference']
        self.low_allergy = data['lowAllergy']

        self.mobility = data['mobility']
        self.bringing_dog = data['bringingDog']

        self.save()