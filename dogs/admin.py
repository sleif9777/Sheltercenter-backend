from django.contrib import admin

from .models import Dog


class DogAdmin(admin.ModelAdmin):
    autocomplete_fields = ["interest_adopters"]


admin.site.register(Dog, DogAdmin)