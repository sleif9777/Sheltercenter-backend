import datetime

from django.core import mail
from django.utils import timezone

from appointment_bases.enums import AppointmentTypes
from appointments.enums import OutcomeTypes
from appointments.models import Appointment
from bookings.enums import BookingStatus
from bookings.models import Booking
from pending_adoptions.enums import CircumstanceOptions, PendingAdoptionStatus

from .base import SmokeTestCase, local_instant


class AuthTests(SmokeTestCase):
    def test_login_returns_tokens_that_authenticate_and_refresh(self) -> None:
        anon = self.client_for(None)
        resp = anon.get("/UserProfiles/LogIn/", {"primaryEmail": self.adopter_user.primary_email})
        self.assertStatus(resp, 202)
        body = resp.json()
        self.assertEqual(body["user"]["adopterID"], self.adopter.id)

        bearer = self.client_for(None)
        bearer.credentials(HTTP_AUTHORIZATION=f"Bearer {body['accessToken']}")
        self.assertStatus(
            bearer.get("/Adopters/GetCalendarRestrictionStatus/", {"adopterID": self.adopter.id}),
            200,
        )

        refreshed = anon.post(
            "/auth/token/refresh/", {"refresh": body["refreshToken"]}, format="json"
        )
        self.assertStatus(refreshed, 200)
        self.assertIn("access", refreshed.json())

        verified = anon.post("/auth/token/verify/", {"token": body["accessToken"]}, format="json")
        self.assertStatus(verified, 200)

    def test_login_unknown_email_is_rejected(self) -> None:
        resp = self.client_for(None).get(
            "/UserProfiles/LogIn/", {"primaryEmail": "nobody@x.invalid"}
        )
        self.assertStatus(resp, 401)

    def test_unauthenticated_requests_are_rejected(self) -> None:
        self.assertStatus(self.client_for(None).get("/Appointments/GetEmptyDates/"), 401)

    def test_adopter_cannot_use_staff_endpoints(self) -> None:
        resp = self.client_for(self.adopter_user).get("/Appointments/GetReportingStats/")
        self.assertStatus(resp, 403)

    def test_adopter_cannot_read_another_adopters_data(self) -> None:
        resp = self.client_for(self.adopter_user).get(
            "/Adopters/GetAdopterPreferences/", {"adopterID": self.other_adopter.id}
        )
        self.assertStatus(resp, 403)


class StaffGetEndpointTests(SmokeTestCase):
    """Every staff-facing GET endpoint runs without error for an admin."""

    def test_staff_get_endpoints(self) -> None:
        today = timezone.localdate().isoformat()
        cases: list[tuple[str, dict]] = [
            ("/Adopters/GetAdopterAlerts/", {"isoDate": today}),
            ("/Adopters/GetAdopterDemographics/", {"adopterID": self.adopter.id}),
            (
                "/Adopters/GetAdopterDirectoryListing/",
                {"filterText": "avery", "includeArchived": "false"},
            ),
            (
                "/Adopters/GetAdopterSelectFieldOptions/",
                {"includeScheduled": "true", "includeArchived": "false"},
            ),
            ("/Adopters/GetRecentlyUploadedAdopters/", {"lookbackDays": 3}),
            ("/TemplateAppointments/GetTemplatesForWeekday/", {"weekday": 3}),
            ("/Appointments/GetAppointmentCardData/", {"apptID": self.booked_appt.id}),
            ("/Appointments/GetAppointmentsMissingOutcomes/", {}),
            (
                "/Appointments/GetContextForDate/",
                {"isoDate": self.booked_appt.instant.date().isoformat()},
            ),
            ("/Appointments/GetEmptyDates/", {}),
            ("/Appointments/GetRecentAdoptions/", {}),
            ("/Appointments/GetReportingAppointment/", {"apptID": self.booked_appt.id}),
            ("/Appointments/GetReportingStats/", {}),
            ("/Appointments/GetDayOfWeekStats/", {}),
            ("/Dogs/GetDashboardDogHash/", {}),
            ("/Dogs/GetDogDemographics/", {"dogID": self.dog.id}),
            ("/Dogs/GetDogSelectFieldOptions/", {}),
            ("/Dogs/GetSurrenderDogOptions/", {}),
            ("/Dogs/GetPublishableDogs/", {}),
            ("/PendingAdoptions/GetActivePendingAdoptions/", {}),
            ("/PendingAdoptions/GetPendingAdoptionSelectFieldOptions/", {}),
            (
                "/PendingAdoptions/GetAdopterCurrentPendingAdoptionStatus/",
                {"adopterID": self.other_adopter.id},
            ),
        ]
        client = self.client_for(self.admin_user)
        for path, params in cases:
            with self.subTest(path=path):
                self.assertStatus(client.get(path, params), 200)

    def test_spreadsheet_exports(self) -> None:
        client = self.client_for(self.admin_user)
        xlsx = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        for path, params in [
            (
                "/Appointments/GetContinuityAccessSpreadsheet/",
                {"isoDate": timezone.localdate().isoformat()},
            ),
            ("/Appointments/GetReportingStatsExport/", {}),
        ]:
            with self.subTest(path=path):
                resp = client.get(path, params)
                self.assertStatus(resp, 200)
                self.assertEqual(resp["Content-Type"], xlsx)
                self.assertTrue(resp.content.startswith(b"PK"), "not a valid xlsx (zip) file")

    def test_greeter_can_use_greeter_endpoints(self) -> None:
        resp = self.client_for(self.greeter_user).get(
            "/Adopters/GetAdopterAlerts/", {"isoDate": timezone.localdate().isoformat()}
        )
        self.assertStatus(resp, 200)


class AdopterFlowTests(SmokeTestCase):
    def test_adopter_get_endpoints(self) -> None:
        client = self.client_for(self.adopter_user)
        for path in [
            "/Adopters/GetCalendarRestrictionStatus/",
            "/Adopters/GetAdopterPreferences/",
            "/Dogs/GetWatchlistForAdopter/",
            "/Dogs/GetWatchlistHashForAdopter/",
        ]:
            with self.subTest(path=path):
                self.assertStatus(client.get(path, {"adopterID": self.adopter.id}), 200)

    def test_watchlist_add_and_remove(self) -> None:
        client = self.client_for(self.adopter_user)
        payload = {"adopterID": self.adopter.id, "dogID": self.dog.id}
        self.assertStatus(client.post("/Dogs/AddDogToList/", payload, format="json"), 200)
        self.assertTrue(self.dog.interest_adopters.filter(pk=self.adopter.pk).exists())
        self.assertStatus(client.post("/Dogs/RemoveDogFromList/", payload, format="json"), 200)
        self.assertFalse(self.dog.interest_adopters.filter(pk=self.adopter.pk).exists())

    def test_schedule_appointment_sends_confirmation(self) -> None:
        client = self.client_for(self.other_adopter.user_profile)
        resp = client.post(
            "/Appointments/ScheduleAppointment/",
            {"apptID": self.open_appt.id, "adopterID": self.other_adopter.id},
            format="json",
        )
        self.assertStatus(resp, 201)
        self.assertIsNotNone(self.open_appt.get_current_booking())
        self.assertEqual(len(mail.outbox), 1)

    def test_double_booking_is_rejected(self) -> None:
        resp = self.client_for(self.adopter_user).post(
            "/Appointments/ScheduleAppointment/",
            {"apptID": self.open_appt.id, "adopterID": self.adopter.id},
            format="json",
        )
        self.assertStatus(resp, 409)

    def test_cancel_by_token(self) -> None:
        anon = self.client_for(None)
        token = str(self.booking.cancel_token)
        self.assertStatus(anon.get("/Appointments/GetByToken/", {"token": token}), 200)
        self.assertStatus(
            anon.post("/Appointments/CancelByToken/", {"token": token}, format="json"), 200
        )
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.status, BookingStatus.CANCELLED)

    def test_update_preferences(self) -> None:
        resp = self.client_for(self.adopter_user).post(
            "/Adopters/UpdateAdopterPreferences/",
            {"adopterID": self.adopter.id, "hasFence": True, "lowShed": True},
            format="json",
        )
        self.assertStatus(resp, 200)


class StaffWorkflowTests(SmokeTestCase):
    def test_check_in_then_check_out_as_chosen(self) -> None:
        client = self.client_for(self.admin_user)
        self.assertStatus(
            client.post(
                "/Appointments/CheckInAppointment/",
                {"apptID": self.booked_appt.id, "counselor": "Sam", "clothingDescription": "red"},
                format="json",
            ),
            200,
        )
        self.assertStatus(
            client.post(
                "/Appointments/CheckOutAppointment/",
                {
                    "apptID": self.booked_appt.id,
                    "outcome": OutcomeTypes.CHOSEN,
                    "dogID": str(self.dog.id),
                },
                format="json",
            ),
            200,
        )
        self.adopter_user.refresh_from_db()
        self.assertTrue(self.adopter_user.adoption_completed, "chosen outcome should lock calendar")
        self.assertTrue(self.booked_appt.source_adoption)

    def test_restore_access_sends_email(self) -> None:
        self.adopter.restrict_calendar()
        resp = self.client_for(self.admin_user).post(
            "/Adopters/RestoreCalendarAccess/", {"adopterID": self.adopter.id}, format="json"
        )
        self.assertStatus(resp, 204)
        self.adopter_user.refresh_from_db()
        self.assertFalse(self.adopter_user.adoption_completed)
        self.assertEqual(len(mail.outbox), 1)

    def test_resend_approval_sends_email(self) -> None:
        resp = self.client_for(self.admin_user).post(
            "/Adopters/ResendApproval/", {"adopterID": self.adopter.id}, format="json"
        )
        self.assertStatus(resp, 204)
        self.assertEqual(len(mail.outbox), 1)

    def test_pending_adoption_create_and_status_change(self) -> None:
        client = self.client_for(self.admin_user)
        resp = client.post(
            "/PendingAdoptions/CreatePendingAdoption/",
            {
                "adopterID": self.adopter.id,
                "dogID": str(self.dog.id),
                "dog": self.dog.name,
                "circumstance": CircumstanceOptions.FOSTER,
            },
            format="json",
        )
        self.assertIn(resp.status_code, (200, 201), resp.content[:300])
        resp = client.post(
            "/PendingAdoptions/MarkStatus/",
            {
                "adoptionID": self.pending_adoption.id,
                "status": PendingAdoptionStatus.NEEDS_WELL_CHECK,
                "sendEmail": False,
            },
            format="json",
        )
        self.assertIn(resp.status_code, (200, 204), resp.content[:300])
        self.pending_adoption.refresh_from_db()
        self.assertEqual(self.pending_adoption.status, PendingAdoptionStatus.NEEDS_WELL_CHECK)

    def test_close_and_reopen_date(self) -> None:
        client = self.client_for(self.admin_user)
        date = (timezone.localdate() + datetime.timedelta(days=5)).isoformat()
        for path in ["/ClosedDates/MarkDateAsClosed/", "/ClosedDates/UndoMarkDateAsClosed/"]:
            with self.subTest(path=path):
                resp = client.post(path, {"isoDate": date}, format="json")
                self.assertLess(resp.status_code, 300, resp.content[:300])


class RecentAdoptionsTests(SmokeTestCase):
    def test_recent_adoptions_lists_adoption_and_paperwork_appointments(self) -> None:
        past = Appointment.objects.create(
            type=AppointmentTypes.ADULTS,
            instant=local_instant(-2, 14),
            outcome=OutcomeTypes.ADOPTION,
            chosen_dog=self.dog.name,
        )
        Booking.create_active(self.other_adopter, past)
        paperwork = Appointment.objects.create(
            type=AppointmentTypes.PAPERWORK, instant=local_instant(-1, 11)
        )
        self.pending_adoption.paperwork_appointment = paperwork
        self.pending_adoption.save()

        resp = self.client_for(self.admin_user).get("/Appointments/GetRecentAdoptions/")
        self.assertStatus(resp, 200)
        dogs = sorted(a["dog"] for a in resp.json()["adoptions"])
        self.assertEqual(dogs, sorted([self.dog.name, self.other_dog.name]))


class DashboardTests(SmokeTestCase):
    def ready_to_roll_cards(self) -> list[dict[str, object]]:
        resp = self.client_for(self.admin_user).get("/Dogs/GetDashboardDogHash/")
        self.assertStatus(resp, 200)
        cards: list[dict[str, object]] = resp.json()["hash"]["chosen"]["readyToRoll"]
        return cards

    def test_ready_to_roll_includes_paperwork_appointment_once_booked(self) -> None:
        self.pending_adoption.status = PendingAdoptionStatus.READY_TO_ROLL
        self.pending_adoption.save()
        [card] = self.ready_to_roll_cards()
        self.assertIsNone(card["paperworkAppointmentInst"])

        paperwork = Appointment.objects.create(
            type=AppointmentTypes.PAPERWORK, instant=local_instant(2, 16)
        )
        self.pending_adoption.paperwork_appointment = paperwork
        self.pending_adoption.save()
        [card] = self.ready_to_roll_cards()
        self.assertEqual(
            datetime.datetime.fromisoformat(str(card["paperworkAppointmentInst"])),
            paperwork.instant,
        )
