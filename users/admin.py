from django.contrib import admin

from .models import UserProfile


class UserProfileAdmin(admin.ModelAdmin):
    raw_id_fields = ("adopter_profile",)


admin.site.register(UserProfile, UserProfileAdmin)