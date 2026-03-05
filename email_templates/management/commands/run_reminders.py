import datetime

from django.utils import timezone
from dotenv import load_dotenv

from appointments.models import Appointment
from django.core.management.base import BaseCommand
from email_templates.views import EmailViewSet
from utils import DateTimeUtils


class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        load_dotenv()
        tomorrow = timezone.now() + datetime.timedelta(days=1)
        appointments = [
            appointment
            for appointment in Appointment.objects.filter(
                instant__range=DateTimeUtils.get_range_for_date(tomorrow),
                soft_deleted=False,
            )
            if appointment.has_current_booking
        ]

        for appointment in appointments:
            EmailViewSet().AppointmentReminder(appointment)
