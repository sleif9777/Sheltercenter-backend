import datetime
import io
import os
import time
from collections.abc import Callable
from unittest import mock

from django.core import mail
from django.core.management import call_command
from django.utils import timezone

from dogs.enums import DogSex, DogStatus
from dogs.models import Dog

from .base import SmokeTestCase, local_instant


def shelterluv_dog(
    sl_id: int,
    name: str,
    status: str = "Available for Adoption",
    last_updated: int = 1760000000,
) -> dict:
    return {
        "ID": str(sl_id),
        "Internal-ID": str(sl_id * 10),
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
        "LastUpdatedUnixTime": str(last_updated),
        "LastIntakeUnixTime": "1750000000",
    }


class FakeResponse:
    status_code = 200

    def __init__(self, payload: dict) -> None:
        self.payload = payload

    def json(self) -> dict:
        return self.payload


def fake_shelterluv(
    animals: list[dict],
    unpublished_ids: set[int] = frozenset(),  # type: ignore[assignment]
    events: dict[str, list[dict]] | None = None,
) -> Callable[..., FakeResponse]:
    """Fake requests.get serving the animal list, the publishable subset, and per-animal events."""

    def fake_get(
        url: str, headers: dict, params: dict | None = None, **kwargs: object
    ) -> FakeResponse:
        if url.endswith("/events"):
            internal_id = url.split("/")[-2]
            return FakeResponse({"events": (events or {}).get(internal_id, [])})
        listed = animals
        if (params or {}).get("status_type") == "publishable":
            listed = [a for a in animals if int(a["ID"]) not in unpublished_ids]
        return FakeResponse({"animals": listed, "total_count": len(listed), "has_more": False})

    return fake_get


def filler_dogs() -> list[dict]:
    return [shelterluv_dog(2000 + i, f"Dog {i}") for i in range(20)]


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

    def run_import(self, fake_get: Callable[..., FakeResponse]) -> mock.MagicMock:
        with (
            mock.patch.dict(os.environ, {"SHELTERLUV_API_KEY": "test-key"}),
            mock.patch(
                "dogs.management.commands.import_dogs.requests.get", side_effect=fake_get
            ) as patched_get,
        ):
            call_command("import_dogs", stdout=io.StringIO())
        return patched_get

    def make_dog(self, sl_id: int, name: str, status: DogStatus, **fields: object) -> Dog:
        return Dog.objects.create(
            name=name, shelterluv_id=sl_id, sex=DogSex.FEMALE, status=status, **fields
        )

    def went_home_names(self) -> list[str]:
        response = self.client_for(self.admin_user).get("/Dogs/GetDashboardDogHash/")
        return [dog["name"] for dog in response.json()["hash"]["newlyInHome"]]

    def test_import_keeps_adoption_date_when_adopted_dog_is_edited(self) -> None:
        # Shelterluv bumps LastUpdated for any edit, long after the adoption.
        adopted_on = timezone.localdate() - datetime.timedelta(days=140)
        self.make_dog(
            4000,
            "Madiera",
            DogStatus.HEALTHY_IN_HOME,
            publishable=False,
            unavailable_date=adopted_on,
        )
        self.make_dog(
            4001,
            "Fresh Home",
            DogStatus.HEALTHY_IN_HOME,
            publishable=False,
            unavailable_date=timezone.localdate(),
        )
        now = int(time.time())
        animals = filler_dogs() + [
            shelterluv_dog(4000, "Madiera", "Healthy In Home", last_updated=now),
            shelterluv_dog(4001, "Fresh Home", "Healthy In Home", last_updated=now),
        ]

        patched_get = self.run_import(fake_shelterluv(animals, unpublished_ids={4000, 4001}))

        self.assertEqual(Dog.objects.get(shelterluv_id=4000).unavailable_date, adopted_on)
        self.assertFalse(any(c.args[0].endswith("/events") for c in patched_get.call_args_list))
        names = self.went_home_names()
        self.assertNotIn("Madiera", names)
        self.assertIn("Fresh Home", names)

    def test_import_uses_adoption_event_when_dog_goes_home(self) -> None:
        chosen_on = timezone.localdate() - datetime.timedelta(days=10)
        self.make_dog(
            4100, "Adopted", DogStatus.CHOSEN_SN, publishable=False, unavailable_date=chosen_on
        )
        self.make_dog(
            4101, "No Event", DogStatus.CHOSEN_WC, publishable=False, unavailable_date=chosen_on
        )
        adopted_at = local_instant(-1, 12)
        events = {
            "41000": [
                {"Type": "Intake.Transfer", "Time": str(int(adopted_at.timestamp()) - 86400 * 30)},
                {"Type": "Outcome.Adoption", "Time": str(int(adopted_at.timestamp()))},
            ]
        }
        now = int(time.time())
        animals = filler_dogs() + [
            shelterluv_dog(4100, "Adopted", "Healthy In Home", last_updated=now),
            shelterluv_dog(4101, "No Event", "Healthy In Home", last_updated=now),
        ]

        self.run_import(fake_shelterluv(animals, unpublished_ids={4100, 4101}, events=events))

        self.assertEqual(Dog.objects.get(shelterluv_id=4100).unavailable_date, adopted_at.date())
        # No adoption event to read: fall back to the day the import saw the change.
        self.assertEqual(Dog.objects.get(shelterluv_id=4101).unavailable_date, timezone.localdate())

    def test_import_dates_dog_leaving_the_list_once(self) -> None:
        held_on = timezone.localdate() - datetime.timedelta(days=20)
        self.make_dog(
            4200, "On Hold", DogStatus.UNAVAILABLE, publishable=False, unavailable_date=held_on
        )
        self.make_dog(4201, "Newly Chosen", DogStatus.AVAILABLE_NOW, publishable=True)
        self.make_dog(
            4202, "Chosen Gone", DogStatus.CHOSEN_SN, publishable=True, unavailable_date=held_on
        )
        animals = filler_dogs() + [
            shelterluv_dog(4200, "On Hold", "Hold", last_updated=int(time.time())),
            shelterluv_dog(4201, "Newly Chosen", "Chosen - needs s/n"),
        ]

        self.run_import(fake_shelterluv(animals, unpublished_ids={4200, 4201}))

        self.assertEqual(Dog.objects.get(shelterluv_id=4200).unavailable_date, held_on)
        self.assertEqual(Dog.objects.get(shelterluv_id=4201).unavailable_date, timezone.localdate())
        # Missing from the feed entirely: deactivated, but keeps the day it was chosen.
        chosen_gone = Dog.objects.get(shelterluv_id=4202)
        self.assertFalse(chosen_gone.publishable)
        self.assertEqual(chosen_gone.unavailable_date, held_on)
        self.assertEqual(Dog.objects.get(shelterluv_id=1002).unavailable_date, timezone.localdate())
