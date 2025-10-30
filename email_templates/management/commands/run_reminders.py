import datetime

from django.core.management.base import BaseCommand

from appointments.models import Appointment
from utils.DateTimeUtils import DateTimeUtils

from email_templates.views import EmailViewSet

class Command(BaseCommand):
    help = "Print hello world"

    def handle(self, *args, **kwargs):
        tomorrow = datetime.datetime.now() + datetime.timedelta(days=1)
        appointments = [appointment for appointment in Appointment.objects.filter(
            instant__range=DateTimeUtils.GetRangeForDate(tomorrow), #TODO: flip to tomorrow
            soft_deleted=False
        ) if appointment.has_current_booking]

        for appointment in appointments:
            EmailViewSet().AppointmentReminder(appointment)

