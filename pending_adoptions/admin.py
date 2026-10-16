from django.contrib import admin
from unfold.admin import ModelAdmin
from unfold.contrib.filters.admin import ChoicesDropdownFilter, RangeDateTimeFilter

from .models import PendingAdoption


@admin.register(PendingAdoption)
class PendingAdoptionAdmin(ModelAdmin):
    list_display = (
        "id",
        "dog",
        "adopter",
        "status",
        "circumstance",
        "heartworm_positive",
        "created_instant",
    )
    list_display_links = ("id", "dog")
    list_select_related = ("adopter__user_profile",)
    list_filter = (
        ("status", ChoicesDropdownFilter),
        ("circumstance", ChoicesDropdownFilter),
        "heartworm_positive",
        ("created_instant", RangeDateTimeFilter),
    )
    list_filter_submit = True
    search_fields = (
        "dog",
        "=dogID",
        "adopter__user_profile__first_name",
        "adopter__user_profile__last_name",
        "adopter__primary_email",
    )
    autocomplete_fields = ("adopter", "source_appointment", "paperwork_appointment")
    date_hierarchy = "created_instant"
    ordering = ("-created_instant",)
