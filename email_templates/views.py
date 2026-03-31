from adopters.models import Adopter
from django.utils import timezone
from environment_settings.models import EnvironmentSettings
from pending_adoptions.enums import CircumstanceOptions
from rest_framework import viewsets

from.services import EmailService

class EmailViewSet(viewsets.ViewSet):
    def ApplicationApproved(self, adopter: Adopter):
        recipients = [e for e in [adopter.user_profile.primary_email, adopter.user_profile.secondary_email] if e]
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
                "approved_until_display": adopter.approved_until.strftime("%b %d, %Y")
            }, 
            recipients
        )

        email.send()
        adopter.approval_emailed = True
        adopter.save()

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
            booking.adopter.user_profile.primary_email
        )
        email.send()

    def AppointmentReminder(self, appointment):
        booking = appointment.get_current_booking()
        subject = "Reminder: Your Upcoming Appointment with Saving Grace"

        email = EmailService(
            subject, 
            "appointment_reminder", 
            { 
                "appointment": appointment,
            }, 
            booking.adopter.user_profile.primary_email
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
            booking.adopter.user_profile.primary_email
        )
        email.send()

    def DogChosen(self, appointment):
        booking = appointment.get_current_booking()
        subject = "Congratulations on choosing {0}! ({1})".format(
            appointment.source_adoption.dog.title(),
            booking.adopter.user_profile.full_name
        )

        email = EmailService(
            subject, 
            "dog_chosen", 
            { 
                "appointment": appointment,
            }, 
            booking.adopter.user_profile.primary_email
        )
        email.send()

    def DogNoLongerAvailable(self, adopter: Adopter, dog_name: str):
        recipients = [e for e in [adopter.user_profile.primary_email, adopter.user_profile.secondary_email] if e]
        email = EmailService(
            "An update from your watchlist", 
            "dog_no_longer_available", 
            { 
                "adopter": adopter,
                "dog_name": dog_name,
            }, 
            recipients
        )
        email.send()

    def NoDecision(self, appointment, send_sleepover_info: bool):
        booking = appointment.get_current_booking()
        subject = "Hope to see you again soon! ({0})".format(
            booking.adopter.user_profile.full_name
        )

        email = EmailService(
            subject, 
            "no_decision", 
            { 
                "appointment": appointment,
                "host_weekend": send_sleepover_info
            }, 
            booking.adopter.user_profile.primary_email
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
            booking.adopter.user_profile.primary_email
        )
        email.send()

    def AdoptionCreated(self, adoption):
        subject = "Congratulations on choosing {0}!".format(adoption.dog.title())

        email = EmailService(
            subject, 
            "adoption_created", 
            { 
                "adoption": adoption,
                "host_weekend": adoption.circumstance == CircumstanceOptions.HOST_WEEKEND,
                "foster": adoption.circumstance == CircumstanceOptions.FOSTER,
            }, 
            adoption.adopter.user_profile.primary_email
        )
        email.send()

    def ReadyToRoll(self, adoption, custom_message: str):
        subject = "{0} is ready to go home!".format(adoption.dog.title())
        attachments = []

        if adoption.heartworm_positive:
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

        if custom_message.strip(" ") == "":
            template = "ready_to_roll"
            context = { 
                "adoption": adoption,
                "next_bus_day": next_bus_day,
                "today_close": today_close,
                "open_hour": open_hour,
                "close_hour": close_hour
            }
        else:
            template = "generic"
            context = {
                "message": custom_message.replace("\n", "<br />")
            }

        email = EmailService(
            subject, 
            template,
            context,
            adoption.adopter.user_profile.primary_email,
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
            appointment.paperwork_adoption.adopter.user_profile.primary_email
        )
        email.send()

    def GenericMessage(self, user, subject, message, to_adoptions=False):
        if subject == "":
            subject = "A message from Saving Grace NC"
        
        email = EmailService(
            subject,
            "generic",
            {
                "adopter_name": user.disambiguated_name,
                "message": message,
                "to_adoptions": to_adoptions,
            },
            "adoptions@savinggracenc.org" if to_adoptions else user.primary_email,
            user.adopter_profile
        )
        email.send()