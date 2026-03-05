from __future__ import annotations
from collections import OrderedDict
from django.utils import timezone

from .enums import AppointmentTypes
from .models import AppointmentBase

class TemplateHashMapper:
    @staticmethod
    def map_templates(templates: list[AppointmentBase] | list[AppointmentBase]) -> list[dict]: # type: ignore
        grouped = OrderedDict()

        for template in templates:
            time = template.time

            key: int = (time.hour * 100) + time.minute
            label: str = template.time_display

            if key not in grouped:
                grouped[key] = {"key": key, "label": label, "value": []}

            hash_appt = {
                "ID": getattr(template, "id", None),
                "typeDisplay": AppointmentTypes(template.type).label
            }

            grouped[key]["value"].append(hash_appt)

        return sorted(grouped.values(), key=lambda x: x["key"])