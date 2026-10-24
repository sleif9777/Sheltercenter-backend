from bookings.enums import BookingStatus
from bookings.models import Booking

from .base import SmokeTestCase


class CalendarRestrictionStatusTests(SmokeTestCase):
    def get_status(self) -> dict[str, object]:
        resp = self.client_for(self.adopter_user).get(
            "/Adopters/GetCalendarRestrictionStatus/", {"adopterID": self.adopter.id}
        )
        self.assertStatus(resp, 200)
        body: dict[str, object] = resp.json()
        return body

    def test_returns_active_booking_as_current_appt(self) -> None:
        body = self.get_status()
        self.assertFalse(body["restrictCalendar"])
        self.assertEqual(body["currentAppt"], self.adopter.get_current_appointment_summary())
        self.assertEqual(body["currentAppt"]["ID"], self.booked_appt.id)  # type: ignore[index]

    def test_current_appt_clears_once_booking_is_no_longer_active(self) -> None:
        Booking.objects.filter(pk=self.booking.pk).update(status=BookingStatus.COMPLETED)
        self.assertIsNone(self.get_status()["currentAppt"])

    def test_login_matches_status_endpoint(self) -> None:
        resp = self.client_for(None).get(
            "/UserProfiles/LogIn/", {"primaryEmail": self.adopter_user.primary_email}
        )
        self.assertStatus(resp, 202)
        self.assertEqual(resp.json()["user"]["currentAppt"], self.get_status()["currentAppt"])
