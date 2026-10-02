from django.contrib import admin

from .models import Appointment


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    raw_id_fields = ("surrendered_dog_instance",)
    list_display = ("id", "instant", "type", "outcome", "soft_deleted")
    list_filter = ("type", "outcome", "soft_deleted")
    search_fields = ("appointment_notes", "chosen_dog", "surrendered_dog")
