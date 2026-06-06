from django.contrib import admin

from .models import Adopter


class AdopterAdmin(admin.ModelAdmin):
    search_fields = ["primary_email"]


admin.site.register(Adopter, AdopterAdmin)