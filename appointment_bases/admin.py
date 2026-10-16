from django.contrib import admin
from unfold.admin import ModelAdmin
from unfold.contrib.filters.admin import ChoicesDropdownFilter

from .models import AppointmentBase


@admin.register(AppointmentBase)
class AppointmentBaseAdmin(ModelAdmin):
    list_display = ("id", "weekday", "time", "type")
    list_filter = ("weekday", ("type", ChoicesDropdownFilter))
    ordering = ("weekday", "time")
