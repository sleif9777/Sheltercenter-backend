from django.contrib import admin

from .models import Adopter, AdopterUploadEvent


class AdopterAdmin(admin.ModelAdmin):
    search_fields = ["primary_email"]


admin.site.register(Adopter, AdopterAdmin)
admin.site.register(AdopterUploadEvent)