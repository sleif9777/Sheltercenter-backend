from django.contrib import admin
from unfold.admin import ModelAdmin

from .models import ClosedDate


@admin.register(ClosedDate)
class ClosedDateAdmin(ModelAdmin):
    list_display = ("id", "date")
    date_hierarchy = "date"
    ordering = ("-date",)
