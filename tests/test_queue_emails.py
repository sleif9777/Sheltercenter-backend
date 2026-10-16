import datetime

from django.core import mail
from django.utils import timezone

from appointment_bases.enums import AppointmentTypes
from appointments.models import Appointment
from bookings.models import Booking
from users.enums import SecurityLevel

from .base import SmokeTestCase


def instant_at(hour: int, minute: int = 0, days: int = 2) -> datetime.datetime:
    day = timezone.localdate() + datetime.timedelta(days=days)
    return timezone.make_aware(datetime.datetime.combine(day, datetime.time(hour, minute)))


class QueueEmailTests(SmokeTestCase):
    def book(self, hour: int, minute: int = 0, name: str = "q") -> Booking:
        appt = Appointment.objects.create(
            type=AppointmentTypes.ADULTS, instant=instant_at(hour, minute)
        )
        adopter, _ = self.make_adopter(name.title(), "Queue", f"{name}@example.invalid")
        return Booking.create_active(adopter, appt)

    def get_queue(self) -> list[dict]:
        iso_date = (timezone.localdate() + datetime.timedelta(days=2)).isoformat()
        resp = self.client_for(self.admin_user).get(
            "/Appointments/GetQueueForDate/", {"isoDate": iso_date}
        )
        self.assertStatus(resp, 200)
        return resp.json()["queue"]

    def test_orders_by_slot_then_booking_time_and_stops_at_four(self) -> None:
        late = self.book(12, name="late")
        early = self.book(12, name="early")
        early.created = late.created - datetime.timedelta(hours=1)
        early.save()
        two = self.book(14, name="two")
        four = self.book(16, name="four")
        self.book(17, name="five")
        Appointment.objects.create(type=AppointmentTypes.PAPERWORK, instant=instant_at(15))

        ids = [row["apptID"] for row in self.get_queue()]
        expected = [early, late, two, four]
        self.assertEqual(ids, [b.appointment.id for b in expected])

    def test_without_four_pm_slot_includes_first_slot_after(self) -> None:
        first = self.book(15, name="first")
        after = self.book(16, 30, name="after")
        self.book(17, name="later")

        ids = [row["apptID"] for row in self.get_queue()]
        self.assertEqual(ids, [first.appointment.id, after.appointment.id])

    def test_day_ending_before_four_includes_every_slot(self) -> None:
        a = self.book(12, name="a")
        b = self.book(14, name="b")
        # An open slot still counts as a timeslot for the cutoff
        Appointment.objects.create(type=AppointmentTypes.ADULTS, instant=instant_at(15))

        ids = [row["apptID"] for row in self.get_queue()]
        self.assertEqual(ids, [a.appointment.id, b.appointment.id])

    def test_send_emails_positions_and_marks_sent(self) -> None:
        a = self.book(12, name="a")
        b = self.book(14, name="b")

        resp = self.client_for(self.admin_user).post(
            "/Appointments/SendQueueEmails/",
            {
                "entries": [
                    {"apptID": b.appointment.id, "position": 1},
                    {"apptID": a.appointment.id, "position": 2},
                ]
            },
            format="json",
        )
        self.assertStatus(resp, 200)
        self.assertEqual(resp.json(), {"sent": 2, "failed": []})

        self.assertEqual(len(mail.outbox), 2)
        first_html = mail.outbox[0].alternatives[0][0]
        self.assertIn("#1", first_html)
        self.assertIn("Ada Admin", first_html)
        self.assertIn("on ", first_html)

        a.refresh_from_db()
        self.assertTrue(a.sent_x_in_queue)
        self.assertTrue(all(row["alreadySent"] for row in self.get_queue()))

    def test_requires_admin_or_superuser(self) -> None:
        a = self.book(12, name="a")
        iso_date = a.appointment.iso_date

        for level in (SecurityLevel.GREETER, SecurityLevel.DASHBOARD):
            with self.subTest(level=level.name):
                client = self.client_for(self.make_staff(level))
                resp = client.post(
                    "/Appointments/SendQueueEmails/",
                    {"entries": [{"apptID": a.appointment.id, "position": 1}]},
                    format="json",
                )
                self.assertStatus(resp, 403)
                self.assertStatus(
                    client.get("/Appointments/GetQueueForDate/", {"isoDate": iso_date}), 403
                )

        self.assertEqual(len(mail.outbox), 0)

    def test_allows_admin(self) -> None:
        a = self.book(12, name="a")
        client = self.client_for(self.make_staff(SecurityLevel.ADMIN))

        self.assertStatus(
            client.get("/Appointments/GetQueueForDate/", {"isoDate": a.appointment.iso_date}), 200
        )
        resp = client.post(
            "/Appointments/SendQueueEmails/",
            {"entries": [{"apptID": a.appointment.id, "position": 1}]},
            format="json",
        )
        self.assertStatus(resp, 200)
        self.assertEqual(len(mail.outbox), 1)
