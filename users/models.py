import csv
import datetime
import io
import random
import string
import traceback

import pandas
from adopters.models import Adopter
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.core.validators import validate_email
from django.db import models
from django.utils import timezone
from email_templates.views import EmailViewSet
from utils import DateTimeUtils

from backend import settings

from .enums import SecurityLevel
from .managers import UserProfileManager


# Create your models here.
class UserProfile(AbstractBaseUser, PermissionsMixin):
    # NAME
    first_name = models.CharField(default="", max_length=100, null=False, blank=False)
    last_name = models.CharField(default="", max_length=100, null=False, blank=False)

    @property
    def full_name(self):
        return self.first_name + " " + self.last_name

    @property
    def disambiguated_name(self):
        return self.full_name + " ({0})".format(self.primary_email)

    # LOCATION
    city = models.CharField(default="", max_length=100, null=True, blank=True)
    state = models.CharField(default="", max_length=2, null=True, blank=True)

    @property
    def out_of_state(self):
        return self.state not in ["", "NC", "VA", "SC"]

    # CONTACT INFO
    primary_email = models.EmailField(
        default="",
        max_length=100,
        null=False,
        blank=False,
        unique=True,
        validators=[validate_email],
    )
    secondary_email = models.EmailField(
        default="",
        max_length=100,
        null=True,
        blank=True,
    )
    phone_number = models.CharField(
        default="",
        max_length=50,
        null=True,
        blank=True,
    )

    street_address = models.CharField(
        default="",
        max_length=200,
        null=True,
        blank=True
    )
    postal_code = models.CharField(
        default="",
        max_length=10,
        null=True,
        blank=True
    )

    @property
    def all_emails(self):
        return [email for email in [self.primary_email, self.secondary_email] if email is not None]

    # HISTORY-BASED SECURITY
    registered = models.DateTimeField(auto_now_add=True)
    adoption_completed = models.BooleanField(default=False)

    @property
    def due_for_archive(self):
        if self.archived:
            return False

        now = timezone.now()
        ninety_days_ago = now - datetime.timedelta(days=90)

        # Fetch timestamps safely
        last_uploaded = getattr(self.adopter_profile, "last_uploaded", None)
        last_login = self.last_login
        last_booking = getattr(self.adopter_profile, "last_booking_activity", None)

        # Condition 1:
        # Uploaded over 90 days ago, no bookings or logins
        if (
            last_uploaded
            and last_uploaded < ninety_days_ago
            and not last_login
            and not last_booking
        ):
            return True

        # Condition 2:
        # Last login over 90 days ago, no booking after login, and no re-upload after login
        if last_login and last_login < ninety_days_ago:
            booking_after_login = last_booking and last_booking > last_login
            uploaded_after_login = last_uploaded and last_uploaded > last_login
            if not booking_after_login and not uploaded_after_login:
                return True

        # Condition 3:
        # Last booking over 90 days ago, and no login or upload after booking
        if last_booking and last_booking < ninety_days_ago:
            login_after_booking = last_login and last_login > last_booking
            uploaded_after_booking = last_uploaded and last_uploaded > last_booking
            if not login_after_booking and not uploaded_after_booking:
                return True

        # If none of the above, do not archive
        return False

    # ROLE-BASED SECURITY
    security_level = models.IntegerField(
        choices=SecurityLevel.choices,
        null=False,
        blank=False,
    )
    adopter_profile = models.OneToOneField(
        Adopter, on_delete=models.CASCADE, related_name="user_profile", null=True, blank=True
    )
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)

    email_signature = models.TextField(default="", null=True, blank=True)

    # OTHER RELATIONAL FIELDS
    def __repr__(self):
        return self.disambiguated_name

    def __str__(self):
        return self.disambiguated_name + " [{0}]".format(self.id)

    # ADMINISTRATIVE METHODS
    def update_email(self, new_email):
        self.primary_email = new_email
        self.save()

        self.adopter_profile.primary_email = new_email
        self.adopter_profile.save()

    # TODO: move this to an automated task
    @staticmethod
    def remove_faulty():
        faulty = Adopter.objects.filter(user_profile=None)

        for adopter in faulty:
            adopter.delete()

        users = UserProfile.objects.all()
        archivable = [user for user in users if user.due_for_archive]

        for user in archivable:
            user.archived = True
            user.save()

    # CLASS METADATA
    class Meta:
        ordering = ["first_name", "last_name", "primary_email"]

    USERNAME_FIELD = "primary_email"
    PASSWORD_FIELD = "password"
    REQUIRED_FIELDS = ["first_name", "last_name"]

    objects = UserProfileManager()

    ######## DEPRECATED ##########
    has_acknowledged_faq = models.BooleanField(default=False)  # TODO: remove
    requested_access = models.BooleanField(default=False)  # TODO: remove
    requested_surrender = models.BooleanField(default=False)  # TODO: remove

    # AUTHENTICATION - deprecated but retained
    password = models.CharField(max_length=100, blank=True, null=True)
    otp = models.CharField(max_length=8, null=True, blank=True)
    otp_expiration = models.DateTimeField(null=True, blank=True)
    max_otp_try = models.IntegerField(default=settings.MAX_OTP_TRY)
    otp_max_out = models.DateTimeField(blank=True, null=True)
    archived = models.BooleanField(default=False)

    @property
    def timed_out(self):
        if self.max_otp_try > 0 or self.otp_max_out == None:
            return False

        return timezone.now() < (self.otp_max_out + datetime.timedelta(minutes=15))

    @property
    def otp_expired(self):
        return timezone.now() > self.otp_expiration

    @staticmethod
    def generate_otp():
        valid_letters = string.ascii_uppercase.replace("O", "").replace("I", "")

        four_letters = [random.choice(valid_letters) for _ in range(4)]
        four_digits = [random.choice(string.digits) for _ in range(4)]
        combined = four_letters + four_digits
        random.shuffle(combined)
        return "".join(combined)

    def reset_otp(self):
        self.otp = UserProfile.generate_otp()
        self.otp_expiration = timezone.now() + datetime.timedelta(minutes=15)
        self.max_otp_try = 3
        self.otp_max_out = None
        self.save()

        EmailViewSet().NewOTP(self)

    def failed_authentication(self):
        self.max_otp_try -= 1

        if self.max_otp_try == 0:
            self.otp_max_out = timezone.now()

        self.save()

        return self.max_otp_try == 0

    @property
    def application_expired(self):  # TODO: deprecate and rely only on adopter
        if self.security_level > SecurityLevel.ADOPTER:
            return False

        return self.adopter_profile.approved_until < datetime.date.today()
