import datetime

from django.core import mail
from django.utils import timezone

from appointment_bases.enums import AppointmentTypes
from appointments.models import Appointment
from bookings.models import Booking
from dogs.enums import DogSex, DogStatus
from dogs.models import Dog
from users.enums import SecurityLevel

from .base import SmokeTestCase


def instant_at(hour: int, minute: int = 0, days: int = 2) -> datetime.datetime:
    day = timezone.localdate() + datetime.timedelta(days=days)
    return timezone.make_aware(datetime.datetime.combine(day, datetime.time(hour, minute)))


class QueueEmailTestCase(SmokeTestCase):
    def book(self, hour: int, minute: int = 0, name: str = "q") -> Booking:
        appt = Appointment.objects.create(
            type=AppointmentTypes.ADULTS, instant=instant_at(hour, minute)
        )
        adopter, _ = self.make_adopter(name.title(), "Queue", f"{name}@example.invalid")
        return Booking.create_active(adopter, appt)

    def get_queue_response(self, user=None) -> dict:
        iso_date = (timezone.localdate() + datetime.timedelta(days=2)).isoformat()
        resp = self.client_for(user or self.admin_user).get(
            "/Appointments/GetQueueForDate/", {"isoDate": iso_date}
        )
        self.assertStatus(resp, 200)
        return resp.json()

    def get_queue(self) -> list[dict]:
        return self.get_queue_response()["queue"]

    def send(self, user, payload: dict):
        return self.client_for(user).post("/Appointments/SendQueueEmails/", payload, format="json")

    def make_dog(self, name: str, shelterluv_id: int, status=DogStatus.AVAILABLE_NOW) -> Dog:
        return Dog.objects.create(
            name=name,
            shelterluv_id=shelterluv_id,
            sex=DogSex.MALE,
            status=status,
            publishable=True,
            last_updated=timezone.localdate(),
        )


class QueueEmailTests(QueueEmailTestCase):
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


class QueueEmailCustomizationTests(QueueEmailTestCase):
    """Custom message and popular dogs are superusers only (admin_user is a superuser)."""

    def test_superuser_gets_popular_dogs_from_queued_watchlists(self) -> None:
        a = self.book(12, name="a")
        b = self.book(14, name="b")
        self.book(16, name="four")
        late = self.book(17, name="late")
        luna = self.make_dog("Luna", 2001)
        chosen = self.make_dog("Chosen", 2002, status=DogStatus.CHOSEN_SN)
        luna.interest_adopters.add(a.adopter, b.adopter)
        self.dog.interest_adopters.add(b.adopter)
        chosen.interest_adopters.add(a.adopter, b.adopter)
        # After the 4:00 PM cutoff, so not in the queue
        self.dog.interest_adopters.add(late.adopter)

        data = self.get_queue_response()

        self.assertEqual(
            data["popularDogs"],
            [
                {"dogID": luna.id, "name": "Luna", "watchers": 2},
                {"dogID": self.dog.id, "name": "Biscuit", "watchers": 1},
            ],
        )
        # [DAY] is filled in for the editor; [NUMBER] stays for each adopter
        day = timezone.localdate() + datetime.timedelta(days=2)
        day_phrase = "on {0}".format(day.strftime("%A"))
        self.assertIn("[NUMBER]", data["defaultMessage"])
        self.assertNotIn("[DAY]", data["defaultMessage"])
        self.assertIn(f"Funny Farm {day_phrase}!", data["defaultMessage"])
        # The list goes where [DOGS] is, after an intro staff can reword
        message = data["defaultMessage"]
        self.assertIn(
            f"<p>A few of our pups have quite the fan club {day_phrase}! "
            "Lots of visitors are hoping to meet:</p>[DOGS]",
            message,
        )
        # Greeting and sign-off are editable, like the other message templates
        self.assertTrue(message.startswith('<p><span style="color: #a7396e;">Hi [FIRST NAME],'))
        self.assertLess(message.index("[DOGS]"), message.index("We look forward to seeing you!"))
        self.assertIn("Ada Admin", message)

    def test_admin_does_not_get_customization_options(self) -> None:
        self.book(12, name="a")

        data = self.get_queue_response(self.make_staff(SecurityLevel.ADMIN))

        self.assertNotIn("popularDogs", data)
        self.assertNotIn("defaultMessage", data)

    def test_default_email_fills_in_number_and_day(self) -> None:
        a = self.book(12, name="a")

        self.assertStatus(
            self.send(self.admin_user, {"entries": [{"apptID": a.appointment.id, "position": 4}]}),
            200,
        )

        html = mail.outbox[0].alternatives[0][0]
        self.assertIn("<b>#4</b> in the queue on ", html)
        self.assertNotIn("[NUMBER]", html)
        self.assertNotIn("[DAY]", html)
        self.assertNotIn("fan club", html)
        self.assertNotIn("[DOGS]", html)
        self.assertIn("Hi A,", html)
        self.assertIn("Ada Admin", html)
        self.assertEqual(html.count("Kind regards,"), 1)

    def test_superuser_sends_custom_message_and_popular_dogs(self) -> None:
        a = self.book(12, name="a")
        luna = self.make_dog("Luna", 2001)

        resp = self.send(
            self.admin_user,
            {
                "entries": [{"apptID": a.appointment.id, "position": 2}],
                "message": "<p>Busy day [DAY]! You are #[NUMBER] in the que.</p>",
                "dogIDs": [luna.id, self.dog.id, luna.id],
            },
        )
        self.assertStatus(resp, 200)

        html = mail.outbox[0].alternatives[0][0]
        self.assertIn("You are #2 in the queue.", html)
        self.assertNotIn("[DAY]", html)
        self.assertNotIn("Funny Farm", html)
        self.assertIn("fan club", html)
        self.assertNotIn("hold dogs", html)
        # Listed A-Z, whatever order they were picked in
        self.assertLess(html.index("Biscuit"), html.index("Luna"))
        self.assertEqual(html.count("<b>Luna</b>"), 1)

    def test_lists_dogs_where_the_message_puts_them(self) -> None:
        a = self.book(12, name="a")
        luna = self.make_dog("Luna", 2001)

        resp = self.send(
            self.admin_user,
            {
                "entries": [{"apptID": a.appointment.id, "position": 1}],
                "message": "<p>#[NUMBER]. Folks want:</p>[DOGS]<p>Bring a backup pick!</p>",
                "dogIDs": [luna.id, self.dog.id],
            },
        )
        self.assertStatus(resp, 200)

        html = mail.outbox[0].alternatives[0][0]
        self.assertNotIn("[DOGS]", html)
        self.assertNotIn("fan club", html)
        self.assertLess(html.index("Folks want:"), html.index("Biscuit"))
        self.assertLess(html.index("Biscuit"), html.index("Luna"))
        self.assertLess(html.index("Luna"), html.index("Bring a backup pick!"))

    def test_dogs_token_is_dropped_when_no_dogs_are_picked(self) -> None:
        a = self.book(12, name="a")

        resp = self.send(
            self.admin_user,
            {
                "entries": [{"apptID": a.appointment.id, "position": 1}],
                "message": "<p>#[NUMBER]</p>[DOGS]",
            },
        )
        self.assertStatus(resp, 200)

        html = mail.outbox[0].alternatives[0][0]
        self.assertNotIn("[DOGS]", html)
        self.assertNotIn("<ul>", html)

    def test_fills_in_first_name_escaped(self) -> None:
        a = self.book(12, name="a")
        a.adopter.user_profile.first_name = "Jo <Jo>"
        a.adopter.user_profile.save()

        resp = self.send(
            self.admin_user,
            {
                "entries": [{"apptID": a.appointment.id, "position": 1}],
                "message": "<p>Hey [FIRST NAME]! You are #[NUMBER].</p>",
            },
        )
        self.assertStatus(resp, 200)

        html = mail.outbox[0].alternatives[0][0]
        self.assertIn("Hey Jo &lt;Jo&gt;! You are #1.", html)

    def test_custom_message_must_include_number(self) -> None:
        a = self.book(12, name="a")

        resp = self.send(
            self.admin_user,
            {"entries": [{"apptID": a.appointment.id, "position": 1}], "message": "<p>Hi</p>"},
        )

        self.assertStatus(resp, 400)
        self.assertEqual(len(mail.outbox), 0)

    def test_admin_cannot_customize(self) -> None:
        a = self.book(12, name="a")
        admin = self.make_staff(SecurityLevel.ADMIN)
        entries = [{"apptID": a.appointment.id, "position": 1}]

        for extra in ({"message": "<p>#[NUMBER]</p>"}, {"dogIDs": [self.dog.id]}):
            with self.subTest(extra=extra):
                self.assertStatus(self.send(admin, {"entries": entries, **extra}), 403)

        self.assertEqual(len(mail.outbox), 0)
