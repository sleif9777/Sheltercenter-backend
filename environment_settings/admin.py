from django.contrib import admin
from unfold.admin import ModelAdmin

from .models import EnvironmentSettings


@admin.register(EnvironmentSettings)
class EnvironmentSettingsAdmin(ModelAdmin):
    list_display = ("id", "environment_type", "default_sending_email", "last_dog_import")
