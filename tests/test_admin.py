from django.contrib import admin
from django.test import Client
from django.urls import reverse

from .base import SmokeTestCase


class AdminSiteTests(SmokeTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.web = Client()
        self.web.force_login(self.admin_user)

    def test_index_and_login_pages(self) -> None:
        self.assertStatus(self.web.get("/admin/"), 200)
        self.assertStatus(Client().get("/admin/login/"), 200)

    def test_every_registered_model_list_search_and_change_page(self) -> None:
        for model in admin.site._registry:
            name = f"admin:{model._meta.app_label}_{model._meta.model_name}"
            with self.subTest(model=model.__name__):
                changelist = reverse(f"{name}_changelist")
                self.assertStatus(self.web.get(changelist), 200)
                self.assertStatus(self.web.get(changelist, {"q": "avery"}), 200)
                self.assertStatus(self.web.get(reverse(f"{name}_add")), 200)
                obj = model.objects.first()
                if obj is not None:
                    self.assertStatus(self.web.get(reverse(f"{name}_change", args=[obj.pk])), 200)

    def test_custom_filters_and_autocomplete(self) -> None:
        for url, params in [
            ("/admin/adopters/adopter/", {"approval": "expired"}),
            ("/admin/adopters/adopter/", {"approval": "active", "status__exact": 0}),
            ("/admin/dogs/dog/", {"status__exact": 0, "q": "1001"}),
            ("/admin/appointments/appointment/", {"q": "avery"}),
            (
                "/admin/autocomplete/",
                {
                    "app_label": "dogs",
                    "model_name": "dog",
                    "field_name": "interest_adopters",
                    "term": "avery",
                },
            ),
        ]:
            with self.subTest(url=url, params=params):
                self.assertStatus(self.web.get(url, params), 200)

    def test_non_staff_are_redirected_to_login(self) -> None:
        web = Client()
        web.force_login(self.adopter_user)
        self.assertStatus(web.get("/admin/"), 302)
