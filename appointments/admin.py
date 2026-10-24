from django.contrib import admin
from django.db.models import Prefetch, QuerySet
from django.http import HttpRequest
from unfold.admin import ModelAdmin
from unfold.contrib.filters.admin import ChoicesDropdownFilter, RangeDateTimeFilter

from bookings.enums import BookingStatus
from bookings.models import Booking

from .models import Appointment

CURRENT_BOOKING_STATUSES = [BookingStatus.ACTIVE, BookingStatus.NOSHOW, BookingStatus.COMPLETED]


@admin.register(Appointment)
class AppointmentAdmin(ModelAdmin):
    list_display = ("id", "instant", "type", "adopter", "outcome", "locked", "soft_deleted")
    list_display_links = ("id", "instant")
    list_filter = (
        ("type", ChoicesDropdownFilter),
        ("outcome", ChoicesDropdownFilter),
        "soft_deleted",
        "locked",
        ("instant", RangeDateTimeFilter),
    )
    list_filter_submit = True
    search_fields = (
        "bookings__adopter__user_profile__first_name",
        "bookings__adopter__user_profile__last_name",
        "bookings__adopter__primary_email",
        "appointment_notes",
        "chosen_dog",
        "surrendered_dog",
        "visit_adopter",
    )
    autocomplete_fields = ("surrendered_dog_instance", "primary_appointment", "visit_adoption")
    date_hierarchy = "instant"
    ordering = ("-instant",)

    def get_queryset(self, request: HttpRequest) -> QuerySet:
        # Prefetch current bookings so the adopter column doesn't query per row
        current_bookings = Booking.objects.filter(
            status__in=CURRENT_BOOKING_STATUSES
        ).select_related("adopter__user_profile")
        return (
            super()
            .get_queryset(request)
            .prefetch_related(
                Prefetch("bookings", queryset=current_bookings, to_attr="current_bookings")
            )
        )

    @admin.display(description="Adopter")
    def adopter(self, obj: Appointment) -> str:
        bookings = getattr(obj, "current_bookings", [])
        if bookings and bookings[0].adopter:
            return str(bookings[0].adopter)
        return "-"
