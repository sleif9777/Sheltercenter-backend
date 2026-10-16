"""Characterization tests for the adopter application upload.

The expected values below record how the importer stores each cell today, so the
pandas -> openpyxl rewrite can be checked against identical behavior.
"""

import datetime
import io
from unittest import mock

from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from openpyxl import Workbook

from adopters.enums import ApprovalStatus
from adopters.models import AdopterUploadEvent
from users.models import UserProfile

from .base import SmokeTestCase

COLUMNS = 29


def make_row(**cells: object) -> list[object]:
    row: list[object] = [None] * COLUMNS
    for index, value in cells.items():
        row[int(index.lstrip("c"))] = value
    return row


ACCEPTED = make_row(
    c0=8250001,  # Shelterluv application ID (numeric cell)
    c1="Adoption Application",
    c4="Accepted",
    c12="Interested in hounds",
    c13=55501,  # Shelterluv person ID (numeric cell)
    c14="jordan",
    c15="rivers",
    c17="12 oak st",
    c19="wake forest",
    c20="nc",
    c22=27587,  # postal code (numeric cell)
    c23=9195550101,  # phone (numeric cell)
    c27="Jordan.Rivers@Example.invalid",
    c28="jr.alt@example.invalid",
)
PENDING_WITH_BLANKS = make_row(
    c0=8250002,
    c1="Adoption Application",
    c4="Pending",
    c13=55502,
    c14="casey",
    c15="lane",
    c17="9 elm rd",
    c19="raleigh",
    c20="nc",
    c22=None,  # blank in a numeric column
    c23="919-555-0102",
    c27="casey.lane@example.invalid",
)
FOSTER = make_row(
    c0=8250003,
    c1="Foster Application",
    c4="Accepted",
    c14="fran",
    c15="foster",
    c27="fran@example.invalid",
)
MISSING_EMAIL = make_row(
    c0=8250004, c1="Adoption Application", c4="Accepted", c14="no", c15="email"
)


def build_xlsx(rows: list[list[object]]) -> bytes:
    workbook = Workbook()
    sheet = workbook.active
    sheet.append([f"Header {i}" for i in range(COLUMNS)])
    for row in rows:
        sheet.append(row)
    buffer = io.BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


class SpreadsheetUploadTests(SmokeTestCase):
    def upload(self, rows: list[list[object]]) -> dict:
        upload = SimpleUploadedFile(
            "applications.xlsx",
            build_xlsx(rows),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        resp = self.client_for(self.admin_user).post(
            "/UserProfiles/ImportSpreadsheetBatch/", {"importFile": upload}, format="multipart"
        )
        self.assertLess(resp.status_code, 300, resp.content[:500])
        return resp.json()

    def test_xlsx_upload_creates_and_rejects_expected_rows(self) -> None:
        body = self.upload([ACCEPTED, PENDING_WITH_BLANKS, FOSTER, MISSING_EMAIL])
        results = body.get("results", body)
        self.assertEqual(results["successes"], 2)
        self.assertEqual(results["failures"], 1)
        self.assertEqual([r["email"] for r in results["rejected"]], ["Unknown"])

        self.assertFalse(UserProfile.objects.filter(primary_email="fran@example.invalid").exists())

        jordan = UserProfile.objects.get(primary_email="jordan.rivers@example.invalid")
        self.assertEqual((jordan.first_name, jordan.last_name), ("Jordan", "Rivers"))
        self.assertEqual(
            (jordan.street_address, jordan.city, jordan.state), ("12 Oak St", "Wake Forest", "NC")
        )
        self.assertEqual(jordan.secondary_email, "jr.alt@example.invalid")
        self.assertEqual(jordan.adopter_profile.status, ApprovalStatus.APPROVED)
        self.assertEqual(jordan.adopter_profile.application_comments, "Interested in hounds")

        casey = UserProfile.objects.get(primary_email="casey.lane@example.invalid")
        self.assertEqual(casey.adopter_profile.status, ApprovalStatus.PENDING)
        self.assertEqual(casey.phone_number, "919-555-0102")

        self.assertEqual(AdopterUploadEvent.objects.count(), 2)
        self.assertEqual(len(mail.outbox), 1, "only the accepted adopter gets an approval email")

    def test_numeric_cells_are_stored_as_whole_numbers(self) -> None:
        # pandas stored "55501.0" / "27587.0" whenever a numeric column had a blank cell
        self.upload([ACCEPTED, PENDING_WITH_BLANKS, FOSTER])
        jordan = UserProfile.objects.get(primary_email="jordan.rivers@example.invalid")
        self.assertEqual(jordan.adopter_profile.shelterluv_app_id, "8250001")
        self.assertEqual(jordan.adopter_profile.shelterluv_id, "55501")
        self.assertEqual(jordan.postal_code, "27587")
        self.assertEqual(jordan.phone_number, "9195550101")
        casey = UserProfile.objects.get(primary_email="casey.lane@example.invalid")
        self.assertEqual(casey.postal_code, "")

    def test_blank_rows_are_skipped(self) -> None:
        body = self.upload([ACCEPTED, [None] * COLUMNS, PENDING_WITH_BLANKS])
        results = body.get("results", body)
        self.assertEqual((results["successes"], results["failures"]), (2, 0))

    def test_reupload_updates_instead_of_duplicating(self) -> None:
        self.upload([ACCEPTED])
        body = self.upload([ACCEPTED])
        results = body.get("results", body)
        self.assertEqual(results["updates"], 1)
        self.assertEqual(
            UserProfile.objects.filter(primary_email="jordan.rivers@example.invalid").count(), 1
        )
        self.assertEqual(AdopterUploadEvent.objects.count(), 2)

    def test_approval_email_window_does_not_slide_on_reupload(self) -> None:
        start = timezone.now()

        def upload_at(offset: datetime.timedelta) -> None:
            with mock.patch("django.utils.timezone.now", return_value=start + offset):
                self.upload([ACCEPTED])

        upload_at(datetime.timedelta(0))
        upload_at(datetime.timedelta(days=4))
        upload_at(datetime.timedelta(days=6))
        self.assertEqual(len(mail.outbox), 1, "re-uploads inside the window send nothing")

        # One week after the first email, even though the last upload was a day ago
        upload_at(datetime.timedelta(days=7, hours=1))
        self.assertEqual(len(mail.outbox), 2)
