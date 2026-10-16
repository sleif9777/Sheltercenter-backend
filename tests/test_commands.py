import io
import os
from unittest import mock

from django.core import mail
from django.core.management import call_command

from dogs.enums import DogStatus
from dogs.models import Dog

from .base import SmokeTestCase


def shelterluv_dog(sl_id: int, name: str, status: str = "Available for Adoption") -> dict:
    return {
        "ID": str(sl_id),
        "Type": "Dog",
        "Name": name,
        "Status": status,
        "Sex": "Female",
        "Breed": "Hound Mix",
        "Age": 24,
        "CurrentWeightPounds": "41.5",
        "Description": "A very good dog.",
        "CoverPhoto": "https://example.invalid/photo.jpg",
        "Photos": [],
        "Attributes": [{"AttributeName": "Fun Size", "Publish": "No"}],
        "LastUpdatedUnixTime": "1760000000",
        "LastIntakeUnixTime": "1750000000",
    }


class FakeResponse:
    status_code = 200

    def __init__(self, payload: dict) -> None:
        self.payload = payload

    def json(self) -> dict:
        return self.payload


class ManagementCommandTests(SmokeTestCase):
    def test_run_reminders_emails_tomorrows_bookings(self) -> None:
        call_command("run_reminders")
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("Reminder", mail.outbox[0].subject)

    def test_send_pending_approval_emails_runs(self) -> None:
        call_command("send_pending_approval_emails", stdout=io.StringIO())

    def test_import_dogs_with_fake_shelterluv(self) -> None:
        # Biscuit (1001) stays and is renamed; Pepper (1002) disappears from the feed.
        animals = [shelterluv_dog(1001, "Biscuit Jr")] + [
            shelterluv_dog(2000 + i, f"Dog {i}") for i in range(20)
        ]
        payload = {"animals": animals, "total_count": len(animals), "has_more": False}

        with (
            mock.patch.dict(os.environ, {"SHELTERLUV_API_KEY": "test-key"}),
            mock.patch(
                "dogs.management.commands.import_dogs.requests.get",
                return_value=FakeResponse(payload),
            ) as fake_get,
        ):
            call_command("import_dogs", stdout=io.StringIO())

        self.assertTrue(fake_get.called)
        self.assertTrue(
            all(
                c.kwargs["headers"]["Authorization"] == "Bearer test-key"
                for c in fake_get.call_args_list
            )
        )

        biscuit = Dog.objects.get(shelterluv_id=1001)
        self.assertEqual(biscuit.name, "Biscuit Jr")
        self.assertEqual(biscuit.weight, 41)
        self.assertTrue(biscuit.publishable)
        self.assertEqual(Dog.objects.filter(shelterluv_id__gte=2000).count(), 20)

        pepper = Dog.objects.get(shelterluv_id=1002)
        self.assertFalse(pepper.publishable, "dogs missing from the feed should be deactivated")
        self.assertNotEqual(pepper.status, DogStatus.AVAILABLE_NOW)

    def test_import_dogs_aborts_on_tiny_feed(self) -> None:
        payload = {"animals": [shelterluv_dog(3000, "Lonely")], "total_count": 1, "has_more": False}
        with (
            mock.patch.dict(os.environ, {"SHELTERLUV_API_KEY": "test-key"}),
            mock.patch(
                "dogs.management.commands.import_dogs.requests.get",
                return_value=FakeResponse(payload),
            ),
        ):
            call_command("import_dogs", stdout=io.StringIO())
        self.assertFalse(Dog.objects.filter(shelterluv_id=3000).exists())
        self.assertTrue(Dog.objects.get(shelterluv_id=1001).publishable)
