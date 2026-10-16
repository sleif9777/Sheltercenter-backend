from django.contrib import admin
from unfold.admin import ModelAdmin
from unfold.contrib.filters.admin import ChoicesDropdownFilter, RangeDateTimeFilter

from .models import Booking


@admin.register(Booking)
class BookingAdmin(ModelAdmin):
    list_display = ("id", "adopter", "appointment_instant", "appointment_type", "status", "created")
    list_select_related = ("adopter__user_profile", "appointment")
    list_filter = (
        ("status", ChoicesDropdownFilter),
        ("appointment__type", ChoicesDropdownFilter),
        ("appointment__instant", RangeDateTimeFilter),
        ("created", RangeDateTimeFilter),
    )
    list_filter_submit = True
    search_fields = (
        "adopter__user_profile__first_name",
        "adopter__user_profile__last_name",
        "adopter__primary_email",
        "=appointment__id",
    )
    autocomplete_fields = ("adopter", "appointment")
    date_hierarchy = "created"
    ordering = ("-created",)

    @admin.display(description="Appointment", ordering="appointment__instant")
    def appointment_instant(self, obj: Booking) -> str:
        if obj.appointment:
            return obj.appointment.instant_display
        return "-"

    @admin.display(description="Type", ordering="appointment__type")
    def appointment_type(self, obj: Booking) -> str:
        if obj.appointment:
            return obj.appointment.get_type_display()
        return "-"
