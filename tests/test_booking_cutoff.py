import datetime

from django.core import mail
from django.utils import timezone

from appointment_bases.enums import AppointmentTypes
from appointments.models import Appointment
from users.enums import SecurityLevel
from users.models import UserProfile

from .base import SmokeTestCase


class BookingCutoffTests(SmokeTestCase):
    def appt_in(self, **offset: float) -> Appointment:
        return Appointment.objects.create(
            type=AppointmentTypes.ADULTS, instant=timezone.now() + datetime.timedelta(**offset)
        )

    def book(self, appt: Appointment, user: UserProfile) -> object:
        return self.client_for(user).post(
            "/Appointments/ScheduleAppointment/",
            {"apptID": appt.id, "adopterID": self.other_adopter.id, "hasFence": True},
            format="json",
        )

    def test_adopter_rejected_inside_cutoff(self) -> None:
        appt = self.appt_in(hours=1, minutes=59)

        resp = self.book(appt, self.other_adopter.user_profile)

        self.assertStatus(resp, 409)
        self.assertIn("2 hours in advance", resp.json()["error"])
        self.assertIsNone(appt.get_current_booking())
        self.assertEqual(len(mail.outbox), 0)

        # Rejected requests must not save the submitted preferences either
        self.other_adopter.refresh_from_db()
        self.assertFalse(self.other_adopter.has_fence)

    def test_adopter_rejected_for_past_slot(self) -> None:
        appt = self.appt_in(hours=-1)

        self.assertStatus(self.book(appt, self.other_adopter.user_profile), 409)
        self.assertIsNone(appt.get_current_booking())

    def test_adopter_allowed_outside_cutoff(self) -> None:
        appt = self.appt_in(hours=2, minutes=1)

        self.assertStatus(self.book(appt, self.other_adopter.user_profile), 201)
        self.assertIsNotNone(appt.get_current_booking())

    def test_staff_can_book_inside_cutoff(self) -> None:
        for level in (SecurityLevel.GREETER, SecurityLevel.ADMIN, SecurityLevel.SUPERUSER):
            with self.subTest(level=level.name):
                appt = self.appt_in(minutes=30)
                staff = self.make_staff(level)

                self.assertStatus(self.book(appt, staff), 201)
                self.assertIsNotNone(appt.get_current_booking())

                # Free the adopter up for the next role
                appt.get_current_booking().delete()
