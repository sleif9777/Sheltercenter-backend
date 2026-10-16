from django.core import mail

from appointment_bases.enums import AppointmentTypes
from appointments.models import Appointment
from bookings.enums import BookingStatus
from bookings.models import Booking

from .base import SmokeTestCase, local_instant


class RescheduleTests(SmokeTestCase):
    def reschedule(self, new_appt: Appointment, user=None) -> object:
        return self.client_for(user or self.admin_user).post(
            "/Appointments/RescheduleAppointment/",
            {"apptID": self.booked_appt.id, "newApptID": new_appt.id},
            format="json",
        )

    def test_moves_booking_and_emails_adopter(self) -> None:
        self.booking.sent_limited_puppies = True
        self.booking.save()

        self.assertStatus(self.reschedule(self.open_appt), 200)

        self.booking.refresh_from_db()
        self.assertEqual(self.booking.status, BookingStatus.RESCHEDULED)
        self.assertIsNone(self.booked_appt.get_current_booking())

        new_booking = self.open_appt.get_current_booking()
        self.assertIsNotNone(new_booking)
        self.assertEqual(new_booking.adopter, self.adopter)
        self.assertEqual(new_booking.status, BookingStatus.ACTIVE)
        self.assertNotEqual(new_booking.cancel_token, self.booking.cancel_token)
        self.assertTrue(new_booking.sent_limited_puppies)
        self.assertEqual(self.adopter.get_current_appointment(), self.open_appt)

        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("rescheduled", mail.outbox[0].subject)

    def test_rejects_booked_target(self) -> None:
        Booking.create_active(self.other_adopter, self.open_appt)

        self.assertStatus(self.reschedule(self.open_appt), 409)
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.status, BookingStatus.ACTIVE)
        self.assertEqual(len(mail.outbox), 0)

    def test_rejects_non_adoption_and_past_targets(self) -> None:
        paperwork = Appointment.objects.create(
            type=AppointmentTypes.PAPERWORK, instant=local_instant(1, 16)
        )
        past = Appointment.objects.create(type=AppointmentTypes.ADULTS, instant=local_instant(-1, 12))

        self.assertStatus(self.reschedule(paperwork), 409)
        self.assertStatus(self.reschedule(past), 409)

    def test_rejects_checked_in_appointment(self) -> None:
        self.booked_appt.check_in({})
        self.assertStatus(self.reschedule(self.open_appt), 400)

    def test_requires_admin(self) -> None:
        self.assertStatus(self.reschedule(self.open_appt, user=self.greeter_user), 403)

    def test_open_slots_lists_only_unbooked_adoption_appts(self) -> None:
        Appointment.objects.create(type=AppointmentTypes.PAPERWORK, instant=local_instant(1, 16))
        iso_date = self.open_appt.iso_date

        resp = self.client_for(self.admin_user).get(
            "/Appointments/GetOpenAdoptionSlots/", {"isoDate": iso_date}
        )
        self.assertStatus(resp, 200)

        slots = resp.json()["slots"]
        self.assertEqual([s["key"] for s in slots], [1500])
        self.assertEqual([a["ID"] for a in slots[0]["appts"]], [self.open_appt.id])
