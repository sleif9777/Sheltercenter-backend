from django.core import mail

from appointment_bases.enums import AppointmentTypes
from appointments.models import Appointment
from email_templates.views import EmailViewSet

from .base import SmokeTestCase, local_instant


class EmailRenderingTests(SmokeTestCase):
    """Every email builds, renders and sends through the in-memory backend."""

    def setUp(self) -> None:
        super().setUp()
        self.pending_adoption.source_appointment = self.booked_appt
        self.paperwork_appt = Appointment.objects.create(
            type=AppointmentTypes.PAPERWORK, instant=local_instant(3, 11)
        )
        self.pending_adoption.paperwork_appointment = self.paperwork_appt
        self.pending_adoption.save()
        self.dog.interest_adopters.add(self.adopter)

    def test_every_email_sends(self) -> None:
        emails = EmailViewSet()
        cases = {
            "ApplicationApproved": lambda: emails.ApplicationApproved(self.adopter),
            "AppointmentScheduled": lambda: emails.AppointmentScheduled(self.booked_appt),
            "AppointmentRescheduled": lambda: emails.AppointmentRescheduled(
                self.open_appt, self.booked_appt
            ),
            "AppointmentReminder": lambda: emails.AppointmentReminder(self.booked_appt),
            "AppointmentCanceled": lambda: emails.AppointmentCanceled(self.booked_appt),
            "DogChosen": lambda: emails.DogChosen(self.booked_appt),
            "DogNoLongerAvailable": lambda: emails.DogNoLongerAvailable(self.adopter, self.dog),
            "DogTemporarilyUnavailable": lambda: emails.DogTemporarilyUnavailable(
                self.adopter, self.dog
            ),
            "NoDecision (sleepover)": lambda: emails.NoDecision(self.booked_appt, True),
            "NoDecision": lambda: emails.NoDecision(self.booked_appt, False),
            "NoShow": lambda: emails.NoShow(self.booked_appt),
            "AdoptionCreated": lambda: emails.AdoptionCreated(self.pending_adoption),
            "ReadyToRoll": lambda: emails.ReadyToRoll(self.pending_adoption, "See you soon"),
            "PaperworkScheduled": lambda: emails.PaperworkScheduled(self.paperwork_appt),
            "GenericMessage": lambda: emails.GenericMessage(
                self.adopter_user, "Hello", "Message body"
            ),
            "CalendarAccessRestored": lambda: emails.CalendarAccessRestored(self.adopter),
            "BugReport": lambda: emails.BugReport(self.adopter, "Something broke"),
        }
        for name, send in cases.items():
            with self.subTest(email=name):
                before = len(mail.outbox)
                send()
                self.assertEqual(len(mail.outbox), before + 1, f"{name} did not send")
                message = mail.outbox[-1]
                self.assertTrue(message.subject)
                html = message.alternatives[0][0] if message.alternatives else ""
                self.assertIn("<", html, f"{name} has no HTML body")
                self.assertNotIn("{{", html, f"{name} has unrendered template tags")

    def test_non_production_redirects_to_test_recipient(self) -> None:
        EmailViewSet().CalendarAccessRestored(self.adopter)
        message = mail.outbox[-1]
        self.assertEqual(message.to, ["test-recipient@example.invalid"])
        self.assertTrue(message.subject.startswith("[TEST EMAIL]"))
