from django.contrib import admin
from django.contrib.auth.admin import GroupAdmin as BaseGroupAdmin
from django.contrib.auth.models import Group
from unfold.admin import ModelAdmin
from unfold.contrib.filters.admin import ChoicesDropdownFilter, RangeDateTimeFilter

from .models import UserProfile


@admin.register(UserProfile)
class UserProfileAdmin(ModelAdmin):
    list_display = (
        "id",
        "first_name",
        "last_name",
        "primary_email",
        "phone_number",
        "security_level",
        "adoption_completed",
        "archived",
        "registered",
    )
    list_display_links = ("id", "first_name", "last_name")
    list_filter = (
        ("security_level", ChoicesDropdownFilter),
        "is_staff",
        "archived",
        "adoption_completed",
        ("registered", RangeDateTimeFilter),
    )
    list_filter_submit = True
    search_fields = [
        "first_name",
        "last_name",
        "primary_email",
        "secondary_email",
        "phone_number",
    ]
    autocomplete_fields = ("adopter_profile",)


# Re-register Group so it picks up the Unfold theme
admin.site.unregister(Group)


@admin.register(Group)
class GroupAdmin(BaseGroupAdmin, ModelAdmin):
    pass
