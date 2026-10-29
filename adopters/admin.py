from datetime import date

from django.contrib import admin
from django.db.models import QuerySet
from django.http import HttpRequest
from unfold.admin import ModelAdmin
from unfold.contrib.filters.admin import (
    ChoicesDropdownFilter,
    RangeDateFilter,
    RangeDateTimeFilter,
)

from .models import Adopter, AdopterUploadEvent

ADOPTER_SEARCH_FIELDS = [
    "user_profile__first_name",
    "user_profile__last_name",
    "primary_email",
    "user_profile__secondary_email",
    "user_profile__phone_number",
]


class ApprovalExpiredFilter(admin.SimpleListFilter):
    title = "approval"
    parameter_name = "approval"

    def lookups(self, request: HttpRequest, model_admin: admin.ModelAdmin) -> list[tuple[str, str]]:
        return [("active", "Active"), ("expired", "Expired")]

    def queryset(self, request: HttpRequest, queryset: QuerySet) -> QuerySet:
        if self.value() == "active":
            return queryset.filter(approved_until__gte=date.today())
        if self.value() == "expired":
            return queryset.filter(approved_until__lt=date.today())
        return queryset


@admin.register(Adopter)
class AdopterAdmin(ModelAdmin):
    list_display = (
        "id",
        "name",
        "primary_email",
        "status",
        "approved_until",
        "last_uploaded",
        "adoption_completed",
    )
    list_display_links = ("id", "name")
    list_select_related = ("user_profile",)
    list_filter = (
        ("status", ChoicesDropdownFilter),
        ApprovalExpiredFilter,
        "approval_emailed",
        "user_profile__adoption_completed",
        "chatbot_enabled",
        ("approved_until", RangeDateFilter),
        ("last_uploaded", RangeDateTimeFilter),
    )
    list_filter_submit = True
    search_fields = ADOPTER_SEARCH_FIELDS + ["shelterluv_app_id", "shelterluv_id"]
    ordering = ("user_profile__first_name", "user_profile__last_name")

    @admin.display(description="Name", ordering="user_profile__first_name")
    def name(self, obj: Adopter) -> str:
        if hasattr(obj, "user_profile"):
            return obj.user_profile.full_name
        return "-"

    @admin.display(description="Adoption completed", boolean=True)
    def adoption_completed(self, obj: Adopter) -> bool | None:
        if hasattr(obj, "user_profile"):
            return obj.user_profile.adoption_completed
        return None


@admin.register(AdopterUploadEvent)
class AdopterUploadEventAdmin(ModelAdmin):
    list_display = ("id", "adopter", "shelterluv_app_id", "uploaded_at")
    list_select_related = ("adopter__user_profile",)
    list_filter = (("uploaded_at", RangeDateTimeFilter),)
    list_filter_submit = True
    search_fields = ["adopter__" + f for f in ADOPTER_SEARCH_FIELDS] + ["shelterluv_app_id"]
    autocomplete_fields = ("adopter",)
    date_hierarchy = "uploaded_at"
    ordering = ("-id",)
