from django.core.files.uploadedfile import SimpleUploadedFile

from adopters.enums import ApprovalStatus
from adopters.models import Adopter
from pending_adoptions.enums import CircumstanceOptions, PendingAdoptionStatus
from pending_adoptions.models import PendingAdoption
from users.enums import FormContexts

from .base import SmokeTestCase
from .test_uploads import ACCEPTED, build_xlsx

EMAIL = "jordan.rivers@example.invalid"
NEW_APPLICATION = [8250099, *ACCEPTED[1:]]
SECOND_APPLICATION = [8250100, *ACCEPTED[1:]]


class ReapprovalRestoresCalendarTests(SmokeTestCase):
    """Re-approving a past adopter unlocks the calendar their completed adoption locked."""

    def upload(self, rows: list[list[object]]) -> None:
        upload = SimpleUploadedFile(
            "applications.xlsx",
            build_xlsx(rows),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        resp = self.client_for(self.admin_user).post(
            "/UserProfiles/ImportSpreadsheetBatch/", {"importFile": upload}, format="multipart"
        )
        self.assertLess(resp.status_code, 300, resp.content[:500])

    def setUp(self) -> None:
        super().setUp()
        self.upload([ACCEPTED])
        self.jordan().restrict_calendar()

    def jordan(self) -> Adopter:
        return Adopter.objects.get(primary_email=EMAIL)

    def is_restricted(self) -> bool:
        return self.jordan().user_profile.adoption_completed

    def save_form(self, context: FormContexts, status: ApprovalStatus) -> None:
        payload = {
            "context": context,
            "firstName": "Jordan",
            "lastName": "Rivers",
            "primaryEmail": EMAIL,
            "status": status,
        }
        resp = self.client_for(self.admin_user).post("/UserProfiles/SaveUserForm/", payload)
        self.assertLess(resp.status_code, 300, resp.content[:500])

    def test_new_application_restores_access(self) -> None:
        self.upload([NEW_APPLICATION])
        self.assertFalse(self.is_restricted())

    def test_reuploading_the_same_application_keeps_it_locked(self) -> None:
        self.upload([ACCEPTED])
        self.assertTrue(self.is_restricted())

    def test_previously_seen_application_keeps_it_locked(self) -> None:
        # An export that lists an older application after the current one
        self.upload([NEW_APPLICATION])
        self.jordan().restrict_calendar()
        self.upload([ACCEPTED])
        self.assertTrue(self.is_restricted())

    def test_open_pending_adoption_keeps_it_locked(self) -> None:
        PendingAdoption.objects.create(
            circumstance=CircumstanceOptions.HOST_WEEKEND,
            dog="Biscuit",
            adopter=self.jordan(),
            status=PendingAdoptionStatus.NEEDS_SN,
        )
        self.upload([SECOND_APPLICATION])
        self.assertTrue(self.is_restricted())

    def test_unapproved_application_keeps_it_locked(self) -> None:
        pending = [8250101, ACCEPTED[1], ACCEPTED[2], ACCEPTED[3], "Pending", *ACCEPTED[5:]]
        self.upload([pending])
        self.assertTrue(self.is_restricted())

    def test_manual_add_restores_access(self) -> None:
        self.save_form(FormContexts.NEW, ApprovalStatus.APPROVED)
        self.assertFalse(self.is_restricted())

    def test_edit_without_status_change_keeps_it_locked(self) -> None:
        self.save_form(FormContexts.EDIT, ApprovalStatus.APPROVED)
        self.assertTrue(self.is_restricted())

    def test_edit_to_approved_restores_access(self) -> None:
        Adopter.objects.filter(primary_email=EMAIL).update(status=ApprovalStatus.PENDING)
        self.save_form(FormContexts.EDIT, ApprovalStatus.APPROVED)
        self.assertFalse(self.is_restricted())
