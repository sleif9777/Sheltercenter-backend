import csv
import datetime
import io
import random
import string
import traceback

from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.core.validators import validate_email
from django.db import models
from django.utils import timezone
import pandas

from backend import settings

from adopters.models import Adopter
from utils import DateTimeUtils
from email_templates.views import EmailViewSet

from .enums import SecurityLevels
from .managers import UserProfileManager

# Create your models here.
class UserProfile(AbstractBaseUser, PermissionsMixin):
    # DEMOGRAPHICS
    first_name = models.CharField(
        default="", 
        max_length=100, 
        null=False, 
        blank=False
    )
    last_name = models.CharField(
        default="", 
        max_length=100, 
        null=False, 
        blank=False
    )
    city = models.CharField(
        default="", 
        max_length=100, 
        null=True, 
        blank=True
    )
    state = models.CharField(
        default="", 
        max_length=2, 
        null=True, 
        blank=True
    )
    registered = models.DateTimeField(auto_now_add=True)

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

    # AUTHENTICATION
    password = models.CharField(max_length=100, blank=True, null=True)
    otp = models.CharField(max_length=8, null=True, blank=True)
    otp_expiration = models.DateTimeField(null=True, blank=True)
    max_otp_try = models.IntegerField(default=settings.MAX_OTP_TRY)
    otp_max_out = models.DateTimeField(blank=True, null=True)
    archived = models.BooleanField(default=False)

    # HISTORY-BASED SECURITY
    has_acknowledged_faq = models.BooleanField(default=False)
    adoption_completed = models.BooleanField(default=False)
    requested_access = models.BooleanField(default=False)
    requested_surrender = models.BooleanField(default=False)

    # ROLE-BASED SECURITY
    security_level = models.IntegerField(
        choices=SecurityLevels.choices, 
        null=False, 
        blank=False,
    )
    adopter_profile = models.OneToOneField(Adopter, on_delete=models.CASCADE, related_name="user_profile", null=True, blank=True)
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)

    email_signature = models.TextField(default="", null=True, blank=True)

    USERNAME_FIELD = "primary_email"
    PASSWORD_FIELD = "password"
    REQUIRED_FIELDS = ["first_name", "last_name"]

    objects = UserProfileManager()
    # show_fields_on_appt_cards (array field)

    class Meta:
        ordering = ["first_name", "last_name", "primary_email"]
    
    def __repr__(self):
        return self.disambiguated_name
    
    def __str__(self):
        return self.disambiguated_name
    
    @property
    def full_name(self):
        return self.first_name + " " + self.last_name
    
    @property
    def out_of_state(self):
        return self.state not in ["", "NC", "VA", "SC"]

    @property
    def timed_out(self):
        if self.max_otp_try > 0 or self.otp_max_out == None:
            return False
        
        return timezone.now() < (self.otp_max_out + datetime.timedelta(minutes=15))
    
    @property
    def otp_expired(self):
        return timezone.now() > self.otp_expiration
    
    @property
    def application_expired(self):
        if self.security_level > SecurityLevels.ADOPTER:
            return False
                
        return self.adopter_profile.approved_until < datetime.date.today()
    
    def update_from_shelterluv_import(self, data):
        self.first_name = data['first_name'].title()
        self.last_name = data['last_name'].title()
        self.city = data['city'].title()
        self.state = data['state']
        self.phone_number = data['phone_number']

        if 'secondary_email' in data:
            self.secondary_email = data['secondary_email']
        self.save()

    @property
    def disambiguated_name(self):
        return self.full_name + " ({0})".format(self.primary_email)
    
    @property
    def all_emails(self):
        return [email for email in [self.primary_email, self.secondary_email] if email is not None]
    
    @property
    def due_for_archive(self):
        if self.archived:
            return False

        now = timezone.now()
        ninety_days_ago = now - datetime.timedelta(days=90)

        # Fetch timestamps safely
        last_uploaded = getattr(self.adopter_profile, 'last_uploaded', None)
        last_login = self.last_login
        last_booking = getattr(self.adopter_profile, 'last_booking_activity', None)

        # Condition 1:
        # Uploaded over 90 days ago, no bookings or logins
        if last_uploaded and last_uploaded < ninety_days_ago and not last_login and not last_booking:
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

    @staticmethod
    def generate_otp():
        valid_letters = (string.ascii_uppercase
            .replace("O", "")
            .replace("I", "")
        )

        four_letters = [random.choice(valid_letters) for _ in range (4)]
        four_digits = [random.choice(string.digits) for _ in range (4)]
        combined = four_letters + four_digits
        random.shuffle(combined)
        return ''.join(combined)
    
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
    
    ### Shared File Import Functions ###
    @staticmethod
    def run_all_rows_in_batch(all_rows):
        UserProfile.remove_faulty()

        successes, updates, failures = 0, 0, 0
        aversions = []

        for row in all_rows:
            try:
                assert(UserProfile.validate_row_data(row))
                adopter, created, approval_averted, email = UserProfile.update_or_create_from_row(row)
                
                # Update batch counts
                if created:
                    successes += 1
                elif approval_averted and adopter not in aversions:
                    aversions.append(adopter)
                else:
                    updates += 1

                # Add to email batch
                if email is not None:
                    email.send()
                    adopter.approval_emailed = True
                    adopter.save()
            except Exception as e:
                print(e)
                traceback.print_exc()
                failures += 1

        UserProfile.remove_faulty()

        return successes, updates, failures, aversions
    
    @staticmethod
    def validate_row_data(row_data):
        validate_length = [27, 14, 15, 4]
        
        for i in validate_length:
            if len(row_data[i]) == 0:
                return False
            
        return True
    
    @staticmethod
    def update_or_create_from_row(row_data):        
        if "Foster" in row_data[1]:
            return None, False, False, None

        new_status, approval_averted = Adopter.get_application_status(row_data[4], row_data[27])
        email = None

        adopter, adopter_created = Adopter.objects.update_or_create(
            primary_email=row_data[27].lower(),
            defaults={
                "status": new_status,
                "shelterluv_id": row_data[13],
                "shelterluv_app_id": row_data[0],
                "approved_until": Adopter.get_default_approval_date(),
                "application_comments": row_data[12],
            },
            create_defaults={
                "status": new_status,
                "shelterluv_id": row_data[13],
                "shelterluv_app_id": row_data[0],
                "approved_until": Adopter.get_default_approval_date(),
                "application_comments": row_data[12],
            }
        )
        
        try:
            profile, profile_created = UserProfile.objects.update_or_create(
                primary_email=row_data[27].lower(),
                defaults={
                    "first_name": row_data[14].title(),
                    "last_name": row_data[15].title(),
                    "city": row_data[19],
                    "state": row_data[20],
                    "secondary_email": row_data[28],
                    "phone_number": row_data[23],
                    "archived": False
                },
                create_defaults={
                    "adopter_profile": adopter,
                    "first_name": row_data[14].title(),
                    "last_name": row_data[15].title(),
                    "city": row_data[19],
                    "password": None,
                    "state": row_data[20],
                    "secondary_email": row_data[28],
                    "phone_number": row_data[23],
                    "security_level": SecurityLevels.ADOPTER
                }
            )

            if profile_created:
                profile.set_unusable_password()
                profile.save()

            if adopter.send_approval_email():
                email = EmailViewSet().ApplicationApproved(adopter, batch=True)
                
            adopter.last_uploaded = timezone.now()
            adopter.save()
            
            return adopter, (adopter_created and profile_created), approval_averted, email
        except:
            adopter.delete()
            return None, False, False, None

    ### CSV File Import Functions ###
    @staticmethod
    def import_csv_spreadsheet_batch(import_file):
        csv_file = import_file
        decoded_file = csv_file.read().decode('utf-8')
        io_string = io.StringIO(decoded_file)
        all_rows = list(csv.reader(io_string, delimiter=','))
        return UserProfile.run_all_rows_in_batch(all_rows[1:])
    
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
    
    ### XLSX File Import Functions ###
    @staticmethod
    def import_xlsx_spreadsheet_batch(import_file):
        df = pandas.read_excel(import_file)
        all_rows = df.values.tolist()
        return UserProfile.run_all_rows_in_batch(all_rows)
    
    ### Create/Update By Form ###
    @staticmethod
    def create_update_by_form(form_data):
        if form_data["context"] == "Upload":
            new_status, approval_averted = Adopter.get_application_status(
                form_data["status"], 
                form_data["primaryEmail"]
            )
        else:
            new_status, approval_averted = form_data["status"], False

        adopter, adopter_created = Adopter.objects.update_or_create(
            primary_email=form_data["primaryEmail"].lower(),
            defaults={
                "status": new_status,
                "internal_notes": form_data["internalNotes"]
            },
            create_defaults={
                "approved_until": Adopter.get_default_approval_date(),
                "status": form_data["status"],
                "internal_notes": form_data["internalNotes"]
            }
        )

        profile, profile_created = UserProfile.objects.update_or_create(
            primary_email=form_data["primaryEmail"].lower(),
            defaults={
                "first_name": form_data["firstName"].title(),
                "last_name": form_data["lastName"].title(),
                "archived": False
            },
            create_defaults={
                "adopter_profile": adopter,
                "first_name": form_data["firstName"].title(),
                "last_name": form_data["lastName"].title(),
                "security_level": SecurityLevels.ADOPTER,
            }
        )

        if form_data["context"] == "Upload":
            if not adopter_created:
                adopter.approved_until = Adopter.get_default_approval_date()

            if adopter.send_approval_email():
                EmailViewSet().ApplicationApproved(adopter)

            adopter.last_uploaded = timezone.now()
            adopter.save()

        return adopter, (adopter_created and profile_created), approval_averted

    def update_email(self, new_email):
        self.primary_email = new_email
        self.save()

        self.adopter_profile.primary_email = new_email
        self.adopter_profile.save()