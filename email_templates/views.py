import datetime
from django.conf import settings
from django.core.mail import send_mail, EmailMultiAlternatives
from django.shortcuts import render
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.html import strip_tags
from rest_framework import status, viewsets

from environment_settings.models import EnvironmentSettings
from utils import DateTimeUtils
from pending_adoptions.enums import CircumstanceOptions

from.services import EmailService

class EmailViewSet(viewsets.ViewSet):
    def ApplicationApproved(self, adopter, batch=False):
        subject = "Your application has been reviewed: {0}".format(
            adopter.user_profile.full_name.upper()
        )

        if adopter.application_comments and len(adopter.application_comments) > 0:
            subject += " ({0})".format(adopter.application_comments)

        email = EmailService(
            subject, 
            "application_approved", 
            { 
                "adopter": adopter,
            }, 
            adopter.user_profile.all_emails
        )

        if batch:
            return email
        else:
            email.send()

    def AppointmentScheduled(self, appointment):
        booking = appointment.get_current_booking()
        subject = "Your appointment has been scheduled: {0}".format(
            booking.adopter.user_profile.full_name.upper()
        )

        if booking.adopter.application_comments and len(booking.adopter.application_comments) > 0:
            subject += " ({0})".format(booking.adopter.application_comments)

        email = EmailService(
            subject, 
            "appointment_scheduled", 
            { 
                "appointment": appointment,
            }, 
            booking.adopter.user_profile.all_emails
        )
        email.send()

    def AppointmentCanceled(self, appointment):
        booking = appointment.get_current_booking()
        subject = "Your appointment has been canceled: {0}".format(
            booking.adopter.user_profile.full_name.upper()
        )

        if booking.adopter.application_comments and len(booking.adopter.application_comments) > 0:
            subject += " ({0})".format(booking.adopter.application_comments)

        email = EmailService(
            subject, 
            "appointment_canceled", 
            { 
                "appointment": appointment,
            }, 
            booking.adopter.user_profile.all_emails
        )
        email.send()

    def DogChosen(self, appointment):
        booking = appointment.get_current_booking()
        subject = "Congratulations on choosing {0}! ({1})".format(
            appointment.source_adoption.dog,
            booking.adopter.user_profile.full_name
        )

        email = EmailService(
            subject, 
            "dog_chosen", 
            { 
                "appointment": appointment,
            }, 
            booking.adopter.user_profile.all_emails
        )
        email.send()

    def NoDecision(self, appointment, host_weekend):
        booking = appointment.get_current_booking()
        subject = "Hope to see you again soon! ({0})".format(
            booking.adopter.user_profile.full_name
        )

        email = EmailService(
            subject, 
            "no_decision", 
            { 
                "appointment": appointment,
                "host_weekend": host_weekend
            }, 
            booking.adopter.user_profile.all_emails
        )
        email.send()

    def NoShow(self, appointment):
        booking = appointment.get_current_booking()
        subject = "We missed you today!"

        email = EmailService(
            subject, 
            "no_show", 
            { 
                "appointment": appointment,
            }, 
            booking.adopter.user_profile.all_emails
        )
        email.send()

    def AdoptionCreated(self, adoption):
        subject = "Congratulations on choosing {0}!".format(adoption.dog)

        email = EmailService(
            subject, 
            "adoption_created", 
            { 
                "adoption": adoption,
                "host_weekend": adoption.circumstance == CircumstanceOptions.HOST_WEEKEND,
                "foster": adoption.circumstance == CircumstanceOptions.FOSTER,
            }, 
            adoption.adopter.user_profile.all_emails
        )
        email.send()

    def ReadyToRoll(self, adoption):
        subject = "{0} is ready to go home!".format(adoption.dog)
        attachments = []

        if adoption.heartworm_positive:
            # file1 = "media/Heartworm_Postive_Refrence_Sheet_for_ADOPTERS_rev_11_24_2024_clean.docx"
            # file2 = "media/Heartworm_Treatment_Options_0521_v2.docx"
            environment = EnvironmentSettings.objects.get(pk=1)
            attachments.append(environment.fta_doc_1_path)
            attachments.append(environment.fta_doc_2_path)
            attachments = [a for a in attachments if a]

        match timezone.now().weekday():
            case 0 | 1 | 3 | 6: # MON/TUE/THU/SUN
                next_bus_day = "tomorrow"
                today_close = "6:00pm"
                open_hour = "12:00pm" # TUE/WED/FRI
                close_hour = "6:00pm" 
            case 2: # WED
                next_bus_day = "tomorrow"
                today_close = "6:00pm" # WED
                open_hour = "1:00pm" # THU
                close_hour = "6:00pm" # THU
            case 4: # FRI
                next_bus_day = "tomorrow"
                today_close = "6:00pm" # FRI
                open_hour = "12:00pm" # SAT
                close_hour = "3:00pm" # SAT
            case 5: # SAT
                next_bus_day = "on Monday"
                today_close = "3:00pm" # SAT
                open_hour = "12:00pm" # MON
                close_hour = "6:00pm" # MON

        email = EmailService(
            subject, 
            "ready_to_roll", 
            { 
                "adoption": adoption,
                "next_bus_day": next_bus_day,
                "today_close": today_close,
                "open_hour": open_hour,
                "close_hour": close_hour
            }, 
            adoption.adopter.user_profile.all_emails,
            attachments=attachments
        )
        email.send()

    def PaperworkScheduled(self, appointment):
        subject = "Paperwork scheduled: {0} ({1})".format(
            appointment.paperwork_adoption.adopter.user_profile.full_name,
            appointment.source_adoption.dog
        )

        email = EmailService(
            subject, 
            "paperwork_scheduled", 
            { 
                "appointment": appointment,
                "paperwork_type": "FTA" if appointment.paperwork_adoption.heartworm_positive else "adoption"
            }, 
            appointment.paperwork_adoption.adopter.user_profile.all_emails
        )
        email.send()

    def NewOTP(self, user):
        subject = "Your one-time passcode"

        email = EmailService(
            subject, 
            "new_otp", 
            { 
                "user": user    
            }, 
            [user.primary_email]
        )
        email.send(True) 

    def GenericMessage(self, user, subject, message):
        email = EmailService(
            subject,
            "generic",
            {
                "message": message.replace("\n", "<br />")
            },
            user.all_emails
        )
        email.send()