from django.core.files.uploadedfile import SimpleUploadedFile

from adopters.enums import ApprovalStatus

from .base import SmokeTestCase
from .test_uploads import ACCEPTED, build_xlsx


class AdopterApprovalEndpointPermissionTests(SmokeTestCase):
    def test_only_admins_can_approve_adopters(self) -> None:
        form = {
            "firstName": "Avery",
            "lastName": "Adopter",
            "primaryEmail": self.adopter_user.primary_email,
            "status": ApprovalStatus.APPROVED,
        }
        sheet = SimpleUploadedFile("applications.xlsx", build_xlsx([ACCEPTED]))

        for user, expected in [(None, 401), (self.adopter_user, 403), (self.greeter_user, 403)]:
            with self.subTest(user=user):
                client = self.client_for(user)
                self.assertStatus(client.post("/UserProfiles/SaveUserForm/", form), expected)
                sheet.seek(0)
                self.assertStatus(
                    client.post(
                        "/UserProfiles/ImportSpreadsheetBatch/",
                        {"importFile": sheet},
                        format="multipart",
                    ),
                    expected,
                )
