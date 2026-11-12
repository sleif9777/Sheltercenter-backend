from datetime import date

from adopters.models import Adopter
from django.db.models.functions import Lower
from django.template.loader import render_to_string
from django.utils.html import escape
from dogs.enums import DogStatus
from dogs.models import Dog
from environment_settings.models import EnvironmentSettings
from pending_adoptions.enums import CircumstanceOptions
from rest_framework import viewsets
from utils import DateTimeUtils, TextUtils

from .services import EmailService


class EmailViewSet(viewsets.ViewSet):
    # Filled in per adopter in the X in Queue message
    X_IN_QUEUE_NUMBER = "[NUMBER]"
    X_IN_QUEUE_DAY = "[DAY]"
    X_IN_QUEUE_FIRST_NAME = "[FIRST NAME]"
    # Where a custom message lists the popular dogs
    X_IN_QUEUE_DOGS = "[DOGS]"

    @staticmethod
    def _adopter_recipients(adopter: Adopter) -> list[str]:
        return [
            e
            for e in [adopter.user_profile.primary_email, adopter.user_profile.secondary_email]
            if e
        ]

    def ApplicationApproved(self, adopter: Adopter):
        recipients = self._adopter_recipients(adopter)
        subject = EmailService.subject_with_comments(
            "Your application has been reviewed: {0}".format(adopter.user_profile.full_name.upper()),
            adopter.application_comments,
        )

        attachments = []
        environment = EnvironmentSettings.objects.get(pk=1)
        if environment.application_approved_pdf_path:
            attachments.append((environment.application_approved_pdf_path, "SGNC_AdoptionProcess.pdf"))

        email = EmailService(
            subject,
            "application_approved",
            {
                "adopter": adopter,
                "approved_until_display": adopter.approved_until.strftime("%b %d, %Y"),
            },
            recipients,
            attachments=attachments,
        )

        email.send()
        adopter.approval_emailed = True
        adopter.save(update_fields=["approval_emailed"])

    def AppointmentScheduled(self, appointment):
        booking = appointment.get_current_booking()
        subject = EmailService.subject_with_comments(
            "Your appointment has been scheduled: {0}".format(booking.adopter.user_profile.full_name.upper()),
            booking.adopter.application_comments,
        )

        email = EmailService(
            subject,
            "appointment_scheduled",
            {
                "appointment": appointment,
                "cancel_token": booking.cancel_token,
            },
            booking.adopter.user_profile.primary_email,
        )
        email.send()

    def AppointmentRescheduled(self, previous_appointment, appointment):
        booking = appointment.get_current_booking()
        subject = EmailService.subject_with_comments(
            "Your appointment has been rescheduled: {0}".format(booking.adopter.user_profile.full_name.upper()),
            booking.adopter.application_comments,
        )

        email = EmailService(
            subject,
            "appointment_rescheduled",
            {
                "previous_appointment": previous_appointment,
                "appointment": appointment,
                "cancel_token": booking.cancel_token,
            },
            booking.adopter.user_profile.primary_email,
        )
        email.send()

    def AppointmentReminder(self, appointment):
        booking = appointment.get_current_booking()
        adopter = booking.adopter

        watchlist_dogs = Dog.objects.filter(interest_adopters=adopter)
        watchlist_available = [d for d in watchlist_dogs if d.status == DogStatus.AVAILABLE_NOW]
        watchlist_unavailable = [d for d in watchlist_dogs if d.status != DogStatus.AVAILABLE_NOW]

        subject = "Reminder: Your Upcoming Appointment with Saving Grace"

        email = EmailService(
            subject,
            "appointment_reminder",
            {
                "appointment": appointment,
                "watchlist_available": watchlist_available,
                "watchlist_unavailable": watchlist_unavailable,
                "cancel_token": booking.cancel_token,
            },
            adopter.user_profile.primary_email,
        )
        email.send()

    def AppointmentCanceled(self, appointment):
        booking = appointment.get_current_booking()
        subject = EmailService.subject_with_comments(
            "Your appointment has been canceled: {0}".format(booking.adopter.user_profile.full_name.upper()),
            booking.adopter.application_comments,
        )

        email = EmailService(
            subject,
            "appointment_canceled",
            {
                "appointment": appointment,
            },
            booking.adopter.user_profile.primary_email,
        )
        email.send()

    @staticmethod
    def XInQueueDayPhrase(appt_date: date) -> str:
        days_away = (appt_date - DateTimeUtils.get_today()).days
        if days_away == 0:
            return "today"
        if days_away == 1:
            return "tomorrow"
        return "on {0}".format(appt_date.strftime("%A"))

    @staticmethod
    def XInQueueSignature(user) -> str:
        return user.full_name.strip() or "The Adoptions Team"

    @classmethod
    def XInQueueDefaultMessage(
        cls, signature: str, day_phrase: str | None = None, with_dogs: bool = False
    ) -> str:
        message = render_to_string(
            "email_templates/x_in_queue_message.html",
            {
                # Customizers can list popular dogs, so their default leads into the list
                "dogs_intro": (
                    cls.XInQueuePopularDogsIntro(cls.X_IN_QUEUE_DAY) if with_dogs else ""
                ),
                "signature": signature,
            },
        ).strip()
        # Filled in up front for the editor so staff see the actual wording
        return message.replace(cls.X_IN_QUEUE_DAY, day_phrase) if day_phrase else message

    @staticmethod
    def XInQueuePopularDogsIntro(day_phrase: str) -> str:
        return (
            "A few of our pups have quite the fan club {0}! "
            "Lots of visitors are hoping to meet:".format(day_phrase)
        )

    def XInQueue(
        self,
        appointment,
        position: int,
        signature: str,
        message: str | None = None,
        popular_dogs: list[str] | None = None,
    ):
        booking = appointment.get_current_booking()
        adopter = booking.adopter

        day_phrase = self.XInQueueDayPhrase(appointment.local_dt.date())

        body = TextUtils.fix_queue_spelling(message or self.XInQueueDefaultMessage(signature))

        dogs_html = (
            render_to_string(
                "email_templates/x_in_queue_dogs.html", {"popular_dogs": popular_dogs}
            ).strip()
            if popular_dogs
            else ""
        )
        if self.X_IN_QUEUE_DOGS in body:
            body = body.replace(self.X_IN_QUEUE_DOGS, dogs_html)
        elif dogs_html:
            # A message without [DOGS] still gets the dogs, after the message
            body += "<p>{0}</p>{1}".format(self.XInQueuePopularDogsIntro(day_phrase), dogs_html)

        body = (
            body.replace(self.X_IN_QUEUE_NUMBER, str(position))
            .replace(self.X_IN_QUEUE_DAY, day_phrase)
            .replace(self.X_IN_QUEUE_FIRST_NAME, escape(adopter.user_profile.first_name))
        )

        email = EmailService(
            "Your place in the queue: {0}".format(adopter.user_profile.full_name.upper()),
            "x_in_queue",
            {
                "adopter": adopter,
                "appointment": appointment,
                "message": body,
                "position": position,
            },
            self._adopter_recipients(adopter),
        )
        email.send()

    def DogChosen(self, appointment):
        booking = appointment.get_current_booking()
        subject = "Congratulations on choosing {0}! ({1})".format(
            appointment.source_adoption.dog.title(), booking.adopter.user_profile.full_name
        )

        adoption = appointment.source_adoption
        dog = None
        if adoption.dogID:
            try:
                dog = Dog.objects.get(pk=adoption.dogID)
            except Dog.DoesNotExist:
                pass

        email = EmailService(
            subject,
            "dog_chosen",
            {
                "appointment": appointment,
                "dog": dog,
            },
            booking.adopter.user_profile.primary_email,
        )
        email.send()

    @staticmethod
    def _get_watchlist_still_available(adopter: Adopter, exclude_dog: Dog) -> list[Dog]:
        return list(
            Dog.objects.filter(
                interest_adopters=adopter,
                status=DogStatus.AVAILABLE_NOW,
                publishable=True,
            )
            .exclude(pk=exclude_dog.pk)
            .order_by(Lower("name"))
        )

    @staticmethod
    def _get_upcoming_appointment_display(adopter: Adopter) -> str | None:
        appointment = adopter.get_current_appointment()
        if not appointment:
            return None
        return appointment.long_instant_display

    def DogNoLongerAvailable(self, adopter: Adopter, dog: Dog):
        recipients = self._adopter_recipients(adopter)
        email = EmailService(
            "An update from your watchlist",
            "dog_no_longer_available",
            {
                "adopter": adopter,
                "dog_name": dog.name,
                "watchlist_still_available": self._get_watchlist_still_available(adopter, dog),
                "appointment_display": self._get_upcoming_appointment_display(adopter),
            },
            recipients,
        )
        email.send()

    def DogTemporarilyUnavailable(self, adopter: Adopter, dog: Dog):
        recipients = self._adopter_recipients(adopter)
        available_date_phrase = ""
        if dog.available_date and dog.available_date > date.today():
            available_date_phrase = f"on {dog.available_date.strftime('%B %d, %Y')}"
        email = EmailService(
            "An update from your watchlist",
            "dog_temporarily_unavailable",
            {
                "adopter": adopter,
                "dog_name": dog.name,
                "available_date_phrase": available_date_phrase,
                "watchlist_still_available": self._get_watchlist_still_available(adopter, dog),
                "appointment_display": self._get_upcoming_appointment_display(adopter),
            },
            recipients,
        )
        email.send()

    def NoDecision(self, appointment, send_sleepover_info: bool):
        booking = appointment.get_current_booking()
        adopter = booking.adopter
        subject = "Hope to see you again soon! ({0})".format(adopter.user_profile.full_name)

        email = EmailService(
            subject,
            "no_decision",
            {
                "appointment": appointment,
                "host_weekend": send_sleepover_info,
                "approval_active": not adopter.approval_expired,
                "approved_until_display": adopter.approved_until.strftime("%b %d, %Y"),
            },
            booking.adopter.user_profile.primary_email,
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
            booking.adopter.user_profile.primary_email,
        )
        email.send()

    def AdoptionCreated(self, adoption):
        subject = "Congratulations on choosing {0}!".format(adoption.dog.title())

        dog = None
        if adoption.dogID:
            try:
                dog = Dog.objects.get(pk=adoption.dogID)
            except Dog.DoesNotExist:
                pass

        email = EmailService(
            subject,
            "adoption_created",
            {
                "adoption": adoption,
                "host_weekend": adoption.circumstance == CircumstanceOptions.HOST_WEEKEND,
                "foster": adoption.circumstance == CircumstanceOptions.FOSTER,
                "dog": dog,
            },
            adoption.adopter.user_profile.primary_email,
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

        email = EmailService(
            subject,
            "generic",
            {"message": TextUtils.fix_queue_spelling(custom_message)},
            adoption.adopter.user_profile.primary_email,
            attachments=attachments,
        )
        email.send()

    def PaperworkScheduled(self, appointment):
        subject = "Paperwork scheduled: {0} ({1})".format(
            appointment.paperwork_adoption.adopter.user_profile.full_name,
            appointment.paperwork_adoption.dog,
        )

        email = EmailService(
            subject,
            "paperwork_scheduled",
            {
                "appointment": appointment,
                "paperwork_type": (
                    "FTA" if appointment.paperwork_adoption.heartworm_positive else "adoption"
                ),
            },
            appointment.paperwork_adoption.adopter.user_profile.primary_email,
        )
        email.send()

    def GenericMessage(self, user, subject, message, to_adoptions=False):
        if subject == "":
            subject = "Notification from Saving Grace"

        # Staff-written messages only; adopters' own words go to Adoptions unchanged
        if not to_adoptions:
            subject = TextUtils.fix_queue_spelling(subject)
            message = TextUtils.fix_queue_spelling(message)

        email = EmailService(
            subject,
            "generic",
            {
                "adopter_name": user.disambiguated_name,
                "message": message,
                "to_adoptions": to_adoptions,
            },
            "adoptions@savinggracenc.org" if to_adoptions else user.primary_email,
            adopter=user.adopter_profile,
        )
        email.send()

    def CalendarAccessRestored(self, adopter: Adopter):
        recipients = self._adopter_recipients(adopter)
        email = EmailService(
            "Your Saving Grace calendar access has been restored",
            "calendar_access_restored",
            {"adopter": adopter},
            recipients,
        )
        email.send()

    def BugReport(self, adopter: Adopter, bug_description: str):
        email = EmailService(
            f"Message from {adopter.user_profile.full_name} [Issue Report]",
            "bug_report",
            {
                "adopter_name": adopter.user_profile.full_name,
                "bug_description": bug_description,
            },
            "adoptions@savinggracenc.org",
            adopter=adopter,
        )
        email.send(cc_adoptions=True, bcc=["leifersam9@gmail.com"])
