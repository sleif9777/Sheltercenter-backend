from __future__ import annotations
from collections import OrderedDict
from django.utils import timezone

class AppointmentHashMapper:
    @staticmethod
    def map_appointments(appointments: list[Appointment] | list[AppointmentBase]) -> list[dict]: # type: ignore
        grouped = OrderedDict()

        for appointment in appointments:
            instant = appointment.instant

            # Ensure aware datetime (assume UTC from DB)
            if timezone.is_naive(instant):
                instant = timezone.make_aware(instant, timezone.utc)

            local_dt = timezone.localtime(instant).replace(second=0, microsecond=0)

            key: int = (local_dt.hour * 100) + local_dt.minute
            label: str = local_dt.strftime("%I:%M %p").lstrip("0")

            if key not in grouped:
                grouped[key] = {"key": key, "label": label, "value": []}

            hash_appt = {
                "ID": getattr(appointment, "id", None),
            }

            hash_appt["hasCurrentBooking"] = appointment.has_current_booking
            hash_appt["isAdminAppt"] = appointment.is_admin_appointment
            hash_appt["isInProgress"] = appointment.is_checked_in

            grouped[key]["value"].append(hash_appt)

        return sorted(grouped.values(), key=lambda x: x["key"])