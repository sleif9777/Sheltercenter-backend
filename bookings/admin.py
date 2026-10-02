from django.contrib import admin

from .models import Booking


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    raw_id_fields = ("adopter", "appointment")
    list_select_related = ("adopter__user_profile", "appointment")
    list_display = ("id", "get_adopter_name", "get_appointment_instant", "status", "created")
    list_filter = ("status",)
    search_fields = ("adopter__primary_email", "adopter__user_profile__first_name", "adopter__user_profile__last_name")

    @admin.display(description="Adopter")
    def get_adopter_name(self, obj):
        if obj.adopter and obj.adopter.user_profile:
            return obj.adopter.user_profile.disambiguated_name
        return "-"

    @admin.display(description="Appointment")
    def get_appointment_instant(self, obj):
        if obj.appointment:
            return obj.appointment.instant_display
        return "-"
