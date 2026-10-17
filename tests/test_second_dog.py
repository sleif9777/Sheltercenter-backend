"""An adopter choosing two dogs in one visit.

The second dog is recorded on a hidden placeholder appointment linked to the real one, so each
PendingAdoption keeps exactly one source appointment.
"""

from django.core import mail

from appointments.enums import NoDecisionEmailOption, OutcomeTypes
from appointments.models import Appointment
from bookings.enums import BookingStatus
from pending_adoptions.enums import PendingAdoptionStatus
from pending_adoptions.models import PendingAdoption

from .base import SmokeTestCase


class SecondDogCheckOutTests(SmokeTestCase):
    def check_out(self, expected_status: int = 200, **overrides: object) -> None:
        payload: dict[str, object] = {
            "apptID": self.booked_appt.id,
            "outcome": OutcomeTypes.CHOSEN,
            "dogID": str(self.dog.id),
            "noDecisionEmailOption": NoDecisionEmailOption.NO_EMAIL,
            "secondOutcome": OutcomeTypes.CHOSEN,
            "secondDogID": str(self.other_dog.id),
        }
        payload.update(overrides)
        resp = self.client_for(self.admin_user).post(
            "/Appointments/CheckOutAppointment/", payload, format="json"
        )
        self.assertStatus(resp, expected_status)

    def second_dog_appt(self) -> Appointment:
        return Appointment.objects.get(primary_appointment=self.booked_appt)

    def assertCalendarLocked(self, locked: bool) -> None:
        self.adopter_user.refresh_from_db()
        self.assertEqual(self.adopter_user.adoption_completed, locked)

    def test_two_dogs_create_two_adoptions_from_linked_appointments(self) -> None:
        self.check_out()

        second = self.second_dog_appt()
        first_adoption = PendingAdoption.objects.get(source_appointment=self.booked_appt)
        second_adoption = PendingAdoption.objects.get(source_appointment=second)

        self.assertEqual(first_adoption.dogID, self.dog.id)
        self.assertEqual(second_adoption.dogID, self.other_dog.id)
        self.assertEqual(second_adoption.adopter, self.adopter)
        self.assertEqual(second.instant, self.booked_appt.instant)
        self.assertTrue(second.locked)
        self.assertEqual(second.get_current_booking().status, BookingStatus.COMPLETED)
        self.assertCalendarLocked(True)

        # One dog-chosen email per dog and no booking confirmation
        self.assertEqual(len(mail.outbox), 2)
        for message in mail.outbox:
            self.assertIn("Congratulations on choosing", message.subject)

        self.booked_appt.refresh_from_db()
        self.assertEqual(
            self.booked_appt.outcome_value_display,
            f"CHOSEN: {self.dog.name} + CHOSEN: {self.other_dog.name}",
        )

    def test_placeholder_is_not_a_separate_visit(self) -> None:
        self.check_out()

        self.assertEqual(self.adopter.booking_history["completed"], 1)

        # The calendar only lists the real appointment
        date = self.booked_appt.instant.date().isoformat()
        resp = self.client_for(self.admin_user).get(
            "/Appointments/GetContextForDate/", {"isoDate": date}
        )
        self.assertStatus(resp, 200)
        self.assertNotIn(f'"ID": {self.second_dog_appt().id}', resp.content.decode())

    def test_card_data_returns_second_dog_for_prefill(self) -> None:
        self.check_out(secondOutcome=OutcomeTypes.ADOPTION)

        resp = self.client_for(self.admin_user).get(
            "/Appointments/GetAppointmentCardData/", {"apptID": self.booked_appt.id}
        )
        self.assertStatus(resp, 200)
        second_dog = resp.json()["cardData"]["secondDog"]
        self.assertEqual(second_dog["outcome"], OutcomeTypes.ADOPTION)
        self.assertEqual(second_dog["chosenDogID"], self.other_dog.id)

    def test_resubmitting_reuses_placeholder_without_new_emails(self) -> None:
        self.check_out()
        self.check_out()

        self.assertEqual(
            Appointment.objects.filter(primary_appointment=self.booked_appt).count(), 1
        )
        self.assertEqual(PendingAdoption.objects.filter(adopter=self.adopter).count(), 2)
        self.assertEqual(len(mail.outbox), 2)

    def test_unchecking_second_dog_cancels_it_and_keeps_first(self) -> None:
        self.check_out()
        second = self.second_dog_appt()

        self.check_out(secondOutcome=None, secondDogID=None)

        second.refresh_from_db()
        self.assertTrue(second.soft_deleted)
        self.assertEqual(second.bookings.get().status, BookingStatus.CANCELLED)
        self.assertEqual(
            PendingAdoption.objects.get(source_appointment=second).status,
            PendingAdoptionStatus.CANCELED,
        )
        self.assertEqual(
            PendingAdoption.objects.get(source_appointment=self.booked_appt).status,
            PendingAdoptionStatus.CHOSEN,
        )
        self.assertCalendarLocked(True)

    def test_changing_visit_to_no_decision_cancels_both_and_unlocks(self) -> None:
        self.check_out()

        self.check_out(
            outcome=OutcomeTypes.NO_DECISION, dogID=None, secondOutcome=None, secondDogID=None
        )

        statuses = set(
            PendingAdoption.objects.filter(adopter=self.adopter).values_list("status", flat=True)
        )
        self.assertEqual(statuses, {PendingAdoptionStatus.CANCELED})
        self.assertCalendarLocked(False)

    def test_no_decision_with_only_second_dog_adopted_unlocks(self) -> None:
        # The first dog went home the same day, so it has no pending adoption
        self.check_out(outcome=OutcomeTypes.ADOPTION)

        self.check_out(
            outcome=OutcomeTypes.NO_DECISION, dogID=None, secondOutcome=None, secondDogID=None
        )

        self.assertCalendarLocked(False)

    def test_canceling_second_dog_from_chosen_board_hides_placeholder(self) -> None:
        self.check_out()
        second = self.second_dog_appt()
        second_adoption = PendingAdoption.objects.get(source_appointment=second)

        resp = self.client_for(self.admin_user).post(
            "/PendingAdoptions/MarkStatus/",
            {"adoptionID": second_adoption.id, "status": PendingAdoptionStatus.CANCELED},
            format="json",
        )
        self.assertStatus(resp, 200)

        second.refresh_from_db()
        self.assertTrue(second.soft_deleted)
        self.booked_appt.refresh_from_db()
        self.assertEqual(self.booked_appt.outcome, OutcomeTypes.CHOSEN)
        self.assertCalendarLocked(True)

    def test_canceling_first_dog_keeps_calendar_locked_for_second(self) -> None:
        self.check_out()
        first_adoption = PendingAdoption.objects.get(source_appointment=self.booked_appt)

        resp = self.client_for(self.admin_user).post(
            "/PendingAdoptions/MarkStatus/",
            {"adoptionID": first_adoption.id, "status": PendingAdoptionStatus.CANCELED},
            format="json",
        )
        self.assertStatus(resp, 200)

        self.assertCalendarLocked(True)
        self.booked_appt.refresh_from_db()
        self.assertEqual(
            self.booked_appt.outcome_value_display, f"NO DECISION + CHOSEN: {self.other_dog.name}"
        )

        # Staff can still re-save the visit and keep the second dog
        self.check_out(outcome=OutcomeTypes.NO_DECISION, dogID=None)
        self.assertEqual(
            PendingAdoption.objects.get(source_appointment=self.second_dog_appt()).status,
            PendingAdoptionStatus.CHOSEN,
        )

    def test_soft_deleting_visit_hides_placeholder(self) -> None:
        self.check_out()

        resp = self.client_for(self.admin_user).post(
            "/Appointments/SoftDeleteAppointment/", {"apptID": self.booked_appt.id}, format="json"
        )
        self.assertStatus(resp, 200)
        self.assertTrue(self.second_dog_appt().soft_deleted)

    def test_invalid_second_dog_requests_are_rejected(self) -> None:
        self.check_out(400, secondDogID=str(self.dog.id))
        self.check_out(400, secondOutcome=OutcomeTypes.NO_DECISION)
        self.check_out(400, outcome=OutcomeTypes.NO_DECISION, dogID=None)
        self.check_out(400, outcome=OutcomeTypes.NO_SHOW, dogID=None)
        self.assertFalse(Appointment.objects.filter(primary_appointment=self.booked_appt).exists())

    def test_placeholder_cannot_be_checked_out_directly(self) -> None:
        self.check_out()
        second = self.second_dog_appt()

        self.check_out(
            400,
            apptID=second.id,
            dogID=str(self.other_dog.id),
            secondDogID=str(self.dog.id),
        )
