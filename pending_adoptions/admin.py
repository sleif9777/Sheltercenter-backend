from django.contrib import admin

from .models import PendingAdoption


class PendingAdoptionAdmin(admin.ModelAdmin):
    raw_id_fields = ("adopter", "source_appointment", "paperwork_appointment")


admin.site.register(PendingAdoption, PendingAdoptionAdmin)