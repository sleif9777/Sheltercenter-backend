from django.contrib import admin
from unfold.admin import ModelAdmin

from .models import DashboardNote


@admin.register(DashboardNote)
class DashboardNoteAdmin(ModelAdmin):
    list_display = ("id", "display_name", "note", "show_until", "created_instant")
    list_display_links = ("id", "display_name")
    search_fields = ("dog__name", "dog_name", "note")
    autocomplete_fields = ("dog",)
    ordering = ("-created_instant",)
