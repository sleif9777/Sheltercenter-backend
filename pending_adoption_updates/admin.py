from django.contrib import admin
from unfold.admin import ModelAdmin
from unfold.contrib.filters.admin import RangeDateTimeFilter

from .models import PendingAdoptionUpdate


@admin.register(PendingAdoptionUpdate)
class PendingAdoptionUpdateAdmin(ModelAdmin):
    list_display = ("id", "adoption", "instant")
    list_select_related = ("adoption",)
    list_filter = (("instant", RangeDateTimeFilter),)
    list_filter_submit = True
    search_fields = (
        "adoption__dog",
        "adoption__adopter__user_profile__first_name",
        "adoption__adopter__user_profile__last_name",
        "adoption__adopter__primary_email",
    )
    autocomplete_fields = ("adoption",)
    date_hierarchy = "instant"
    ordering = ("-instant",)
