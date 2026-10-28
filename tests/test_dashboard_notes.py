"""Notes on the dashboard's Notes tab, added and removed by admins and superusers."""

import datetime

from django.utils import timezone

from dashboard_notes.models import DashboardNote
from dogs.models import Dog
from users.enums import SecurityLevel
from users.models import UserProfile

from .base import SmokeTestCase


class DashboardNoteTests(SmokeTestCase):
    def setUp(self) -> None:
        super().setUp()
        # The shared admin_user fixture is SUPERUSER-level
        self.superuser = self.admin_user

    def create(self, user: UserProfile, payload: dict[str, object], expected: int = 201) -> None:
        resp = self.client_for(user).post(
            "/DashboardNotes/CreateDashboardNote/", payload, format="json"
        )
        self.assertStatus(resp, expected)

    def delete(self, user: UserProfile, note: DashboardNote, expected: int = 200) -> None:
        resp = self.client_for(user).post(
            "/DashboardNotes/DeleteDashboardNote/", {"noteID": note.id}, format="json"
        )
        self.assertStatus(resp, expected)

    def dashboard_notes(self, user: UserProfile) -> list[dict[str, object]]:
        resp = self.client_for(user).get("/Dogs/GetDashboardDogHash/")
        self.assertStatus(resp, 200)
        notes: list[dict[str, object]] = resp.json()["notes"]
        return notes

    def test_note_for_a_listed_dog(self) -> None:
        self.create(self.superuser, {"dogID": self.dog.id, "note": "Offsite"})

        note = DashboardNote.objects.get()
        self.assertEqual(note.dog, self.dog)
        self.assertEqual(note.dog_name, "")
        self.assertEqual(note.display_name, "Biscuit")

    def test_note_for_a_dog_not_listed(self) -> None:
        self.create(self.superuser, {"dogName": "  Waffles ", "note": "Trial"})

        note = DashboardNote.objects.get()
        self.assertIsNone(note.dog)
        self.assertEqual(note.dog_name, "Waffles")

    def test_one_dog_can_have_several_notes(self) -> None:
        self.create(self.superuser, {"dogID": self.dog.id, "note": "Offsite"})
        self.create(self.superuser, {"dogID": self.dog.id, "note": "Trial"})

        self.assertEqual(self.dog.dashboard_notes.count(), 2)

    def test_needs_exactly_one_of_dog_or_name(self) -> None:
        self.create(self.superuser, {"note": "Offsite"}, 400)
        self.create(self.superuser, {"dogName": "   ", "note": "Offsite"}, 400)
        self.create(self.superuser, {"dogID": self.dog.id, "dogName": "Waffles", "note": "x"}, 400)
        self.create(self.superuser, {"dogID": 999999, "note": "Offsite"}, 400)
        self.create(self.superuser, {"dogName": "Waffles", "note": ""}, 400)
        self.assertFalse(DashboardNote.objects.exists())

    def test_deleting_a_note_keeps_the_dog(self) -> None:
        note = DashboardNote.objects.create(dog=self.dog, note="Offsite")

        self.delete(self.superuser, note)

        self.assertFalse(DashboardNote.objects.exists())
        self.assertTrue(Dog.objects.filter(pk=self.dog.pk).exists())

    def test_deleting_an_already_deleted_note_is_harmless(self) -> None:
        note = DashboardNote.objects.create(dog_name="Waffles", note="Trial")
        note_copy = DashboardNote.objects.get(pk=note.pk)
        note.delete()

        self.delete(self.superuser, note_copy)

    def test_admins_can_add_and_remove(self) -> None:
        admin = self.make_staff(SecurityLevel.ADMIN)
        self.create(admin, {"dogID": self.dog.id, "note": "Offsite"})

        self.delete(admin, DashboardNote.objects.get())

        self.assertFalse(DashboardNote.objects.exists())

    def test_only_admins_and_superusers_can_add_or_remove(self) -> None:
        note = DashboardNote.objects.create(dog=self.dog, note="Offsite")
        others = [
            self.greeter_user,
            self.adopter_user,
            self.make_staff(SecurityLevel.DASHBOARD),
        ]

        for user in others:
            with self.subTest(level=SecurityLevel(user.security_level).name):
                self.create(user, {"dogID": self.dog.id, "note": "Trial"}, 403)
                self.delete(user, note, 403)

        self.assertEqual(DashboardNote.objects.count(), 1)

    def test_dashboard_lists_notes_with_names_and_photos(self) -> None:
        self.dog.photo_url = "https://example.invalid/biscuit.jpg"
        self.dog.save()
        DashboardNote.objects.create(dog=self.dog, note="Offsite")
        DashboardNote.objects.create(dog_name="Waffles", note="Trial")

        notes = self.dashboard_notes(self.make_staff(SecurityLevel.DASHBOARD))

        self.assertEqual(
            [(n["dogID"], n["dogName"], n["note"]) for n in notes],
            [(self.dog.id, "Biscuit", "Offsite"), (None, "Waffles", "Trial")],
        )
        self.assertEqual(notes[0]["photoURL"], "https://example.invalid/biscuit.jpg")
        self.assertIn("default_dog", str(notes[1]["photoURL"]))

    def test_dashboard_has_no_notes_by_default(self) -> None:
        self.assertEqual(self.dashboard_notes(self.admin_user), [])

    def test_expiry_is_optional(self) -> None:
        today = timezone.localdate()
        self.create(self.superuser, {"dogID": self.dog.id, "note": "Offsite"})
        self.create(
            self.superuser, {"dogID": self.dog.id, "note": "Trial", "showUntil": today.isoformat()}
        )

        self.assertEqual(
            list(DashboardNote.objects.values_list("note", "show_until")),
            [("Offsite", None), ("Trial", today)],
        )

    def test_expiry_cannot_be_in_the_past(self) -> None:
        yesterday = timezone.localdate() - datetime.timedelta(days=1)
        self.create(
            self.superuser,
            {"dogID": self.dog.id, "note": "Offsite", "showUntil": yesterday.isoformat()},
            400,
        )

    def test_notes_show_through_their_last_day_then_are_deleted(self) -> None:
        today = timezone.localdate()
        DashboardNote.objects.create(
            dog=self.dog, note="Expired", show_until=today - datetime.timedelta(days=1)
        )
        DashboardNote.objects.create(dog=self.dog, note="Last day", show_until=today)
        DashboardNote.objects.create(dog=self.dog, note="No expiry")

        notes = self.dashboard_notes(self.admin_user)

        self.assertEqual([n["note"] for n in notes], ["Last day", "No expiry"])
        self.assertEqual(notes[0]["showUntil"], today.isoformat())
        self.assertFalse(DashboardNote.objects.filter(note="Expired").exists())
        self.assertTrue(Dog.objects.filter(pk=self.dog.pk).exists())
