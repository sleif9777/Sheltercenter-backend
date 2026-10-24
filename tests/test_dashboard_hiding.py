import os
from unittest import mock

from django.core.management import call_command
from django.utils import timezone

from dogs.enums import DogSex, DogStatus
from dogs.models import Dog
from users.enums import SecurityLevel

from .base import SmokeTestCase
from .test_commands import fake_shelterluv, filler_dogs, shelterluv_dog


class DashboardHidingTests(SmokeTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.fta_dog = Dog.objects.create(
            name="Mango", shelterluv_id=5001, sex=DogSex.FEMALE, status=DogStatus.FTA
        )
        self.home_dog = Dog.objects.create(
            name="Juniper",
            shelterluv_id=5002,
            sex=DogSex.MALE,
            status=DogStatus.HEALTHY_IN_HOME,
            unavailable_date=timezone.localdate(),
        )

    def dashboard_names(self, user: object, key: str) -> list[str]:
        resp = self.client_for(user).get("/Dogs/GetDashboardDogHash/")  # type: ignore[arg-type]
        self.assertStatus(resp, 200)
        return [dog["name"] for dog in resp.json()["hash"][key]]

    def set_hidden(self, user: object, dog: Dog, hidden: bool) -> object:
        return self.client_for(user).post(  # type: ignore[arg-type]
            "/Dogs/SetDashboardHidden/", {"dogID": dog.id, "hidden": hidden}, format="json"
        )

    def test_hidden_dogs_are_withheld_from_non_admins(self) -> None:
        self.assertStatus(self.set_hidden(self.admin_user, self.fta_dog, True), 200)
        self.assertStatus(self.set_hidden(self.admin_user, self.home_dog, True), 200)

        dashboard_user = self.make_staff(SecurityLevel.DASHBOARD)
        for viewer in (dashboard_user, self.greeter_user):
            self.assertNotIn("Mango", self.dashboard_names(viewer, "fta"))
            self.assertNotIn("Juniper", self.dashboard_names(viewer, "newlyInHome"))

        admin = self.make_staff(SecurityLevel.ADMIN)
        for viewer in (admin, self.admin_user):
            resp = self.client_for(viewer).get("/Dogs/GetDashboardDogHash/").json()
            fta = {dog["name"]: dog["hidden"] for dog in resp["hash"]["fta"]}
            self.assertEqual(fta.get("Mango"), True)

    def test_unhiding_restores_dog(self) -> None:
        self.set_hidden(self.admin_user, self.fta_dog, True)
        self.assertStatus(self.set_hidden(self.admin_user, self.fta_dog, False), 200)
        self.assertIn("Mango", self.dashboard_names(self.greeter_user, "fta"))

    def test_only_admins_and_superusers_can_hide(self) -> None:
        for level in (SecurityLevel.GREETER, SecurityLevel.DASHBOARD):
            self.assertStatus(self.set_hidden(self.make_staff(level), self.fta_dog, True), 403)
        self.assertStatus(self.set_hidden(self.adopter_user, self.fta_dog, True), 403)
        self.fta_dog.refresh_from_db()
        self.assertFalse(self.fta_dog.dashboard_hidden)

    def test_import_clears_hide_on_status_change(self) -> None:
        self.set_hidden(self.admin_user, self.fta_dog, True)
        self.set_hidden(self.admin_user, self.home_dog, True)
        animals = [
            shelterluv_dog(5001, "Mango", status="Healthy In Home"),
            shelterluv_dog(5002, "Juniper", status="Healthy In Home"),
        ] + filler_dogs()

        with (
            mock.patch.dict(os.environ, {"SHELTERLUV_API_KEY": "test-key"}),
            mock.patch(
                "dogs.management.commands.import_dogs.requests.get",
                side_effect=fake_shelterluv(animals, unpublished_ids={5001, 5002}),
            ),
        ):
            call_command("import_dogs", stdout=mock.MagicMock())

        self.fta_dog.refresh_from_db()
        self.home_dog.refresh_from_db()
        self.assertFalse(self.fta_dog.dashboard_hidden, "FTA hide shouldn't carry to Who Went Home")
        self.assertTrue(self.home_dog.dashboard_hidden, "unchanged status keeps the hide")
