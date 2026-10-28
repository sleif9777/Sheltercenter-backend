"""Renaming the dog on a pending adoption from the Chosen Board."""

from appointments.models import Appointment
from pending_adoptions.models import PendingAdoption

from .base import SmokeTestCase


class ChangeDogTests(SmokeTestCase):
    def change_dog(self, adoption: PendingAdoption, new_dog: str) -> None:
        resp = self.client_for(self.admin_user).post(
            "/PendingAdoptions/ChangeDog/",
            {"adoptionID": adoption.id, "newDog": new_dog},
            format="json",
        )
        self.assertStatus(resp, 200)

    def test_adoption_without_source_appointment(self) -> None:
        # Adoptions added from the Chosen Board form have no source appointment
        self.assertIsNone(self.pending_adoption.source_appointment)

        self.change_dog(self.pending_adoption, "Waffles")

        self.pending_adoption.refresh_from_db()
        self.assertEqual(self.pending_adoption.dog, "Waffles")

    def test_new_name_unlinks_old_dog(self) -> None:
        self.change_dog(self.pending_adoption, "Waffles")

        self.pending_adoption.refresh_from_db()
        self.assertIsNone(self.pending_adoption.dogID)

    def test_same_name_keeps_dog_link(self) -> None:
        self.change_dog(self.pending_adoption, self.other_dog.name.upper())

        self.pending_adoption.refresh_from_db()
        self.assertEqual(self.pending_adoption.dogID, self.other_dog.id)

    def test_adoption_with_source_appointment_syncs_chosen_dog(self) -> None:
        self.pending_adoption.source_appointment = self.booked_appt
        self.pending_adoption.save()

        self.change_dog(self.pending_adoption, "Waffles")

        appt = Appointment.objects.get(pk=self.booked_appt.pk)
        self.assertEqual(appt.chosen_dog, "Waffles")
