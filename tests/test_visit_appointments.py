from typing import Any

from appointment_bases.enums import AppointmentTypes
from appointments.models import Appointment
from appointments.serializers import AppointmentCardDataSerializer

from .base import SmokeTestCase, local_instant


class VisitAppointmentTests(SmokeTestCase):
    def create_visit(self, **fields: Any) -> Appointment:
        day = local_instant(2, 11).date()
        response = self.client_for(self.admin_user).post(
            "/Appointments/CreateAppointment/",
            {
                "isoDate": day.isoformat(),
                "hour": 11,
                "minute": 0,
                "type": AppointmentTypes.VISIT,
                "locked": False,
                **fields,
            },
            format="json",
        )
        self.assertStatus(response, 201)
        return Appointment.objects.get(type=AppointmentTypes.VISIT)

    def test_links_selected_adoption(self) -> None:
        visit = self.create_visit(
            pendingAdoptionID=self.pending_adoption.id, notes="Ignored", visitAdopter="Ignored"
        )

        self.assertEqual(visit.visit_adoption, self.pending_adoption)
        self.assertEqual(visit.appointment_notes, "Pepper")
        self.assertEqual(visit.visit_adopter, "Blake Other")
        self.assertEqual(visit.description, "Pepper")

        # Visits don't book the adoption's paperwork slot
        self.pending_adoption.refresh_from_db()
        self.assertIsNone(self.pending_adoption.paperwork_appointment)

    def test_saves_unlisted_dog_without_adopter(self) -> None:
        visit = self.create_visit(pendingAdoptionID=0, notes="Rex")

        self.assertEqual(visit.appointment_notes, "Rex")
        self.assertEqual(visit.visit_adopter, "")
        self.assertNotIn("visitAdopter", AppointmentCardDataSerializer(visit).data)

    def test_saves_unlisted_dog_and_adopter(self) -> None:
        visit = self.create_visit(pendingAdoptionID=0, notes="Rex", visitAdopter="  Jo Smith ")

        self.assertIsNone(visit.visit_adoption)
        self.assertEqual(visit.appointment_notes, "Rex")
        self.assertEqual(visit.visit_adopter, "Jo Smith")

        card = AppointmentCardDataSerializer(visit).data
        self.assertEqual(card["description"], "Rex")
        self.assertEqual(card["visitAdopter"], "Jo Smith")

    def test_legacy_visit_without_adopter(self) -> None:
        visit = Appointment.objects.create(
            type=AppointmentTypes.VISIT, instant=local_instant(1, 11), appointment_notes="Rex"
        )

        card = AppointmentCardDataSerializer(visit).data
        self.assertEqual(card["description"], "Rex")
        self.assertNotIn("visitAdopter", card)

    def test_ignores_visit_adopter_on_other_types(self) -> None:
        day = local_instant(2, 11).date()
        self.client_for(self.admin_user).post(
            "/Appointments/CreateAppointment/",
            {
                "isoDate": day.isoformat(),
                "hour": 11,
                "minute": 0,
                "type": AppointmentTypes.DONATION_DROP_OFF,
                "locked": False,
                "visitAdopter": "Jo Smith",
            },
            format="json",
        )

        appt = Appointment.objects.get(type=AppointmentTypes.DONATION_DROP_OFF)
        self.assertEqual(appt.visit_adopter, "")

    def test_adopters_cannot_load_visit_card(self) -> None:
        visit = Appointment.objects.create(
            type=AppointmentTypes.VISIT,
            instant=local_instant(1, 11),
            appointment_notes="Rex",
            visit_adopter="Jo Smith",
        )

        response = self.client_for(self.adopter_user).get(
            "/Appointments/GetAppointmentCardData/", {"apptID": visit.id}
        )
        self.assertStatus(response, 403)
        self.assertNotIn("cardData", response.json())

        response = self.client_for(self.admin_user).get(
            "/Appointments/GetAppointmentCardData/", {"apptID": visit.id}
        )
        self.assertStatus(response, 200)
        self.assertEqual(response.json()["cardData"]["visitAdopter"], "Jo Smith")
