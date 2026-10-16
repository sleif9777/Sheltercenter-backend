from django.contrib import admin
from unfold.admin import ModelAdmin
from unfold.contrib.filters.admin import ChoicesDropdownFilter, RangeDateFilter

from .models import Dog


@admin.register(Dog)
class DogAdmin(ModelAdmin):
    list_display = (
        "id",
        "name",
        "shelterluv_id",
        "status",
        "sex",
        "breed",
        "age_months",
        "weight",
        "publishable",
        "available_date",
    )
    list_display_links = ("id", "name")
    list_filter = (
        ("status", ChoicesDropdownFilter),
        "sex",
        "publishable",
        "fun_size",
        ("available_date", RangeDateFilter),
        ("last_intake", RangeDateFilter),
    )
    list_filter_submit = True
    search_fields = ["name", "breed", "=shelterluv_id"]
    autocomplete_fields = ["interest_adopters"]
    ordering = ("name",)
