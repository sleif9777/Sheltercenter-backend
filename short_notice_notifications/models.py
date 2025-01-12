import datetime
from enum import Enum
from django.db import models
from django.utils import timezone

from bookings.models import Booking
# from messages.models import Message

class ShortNoticeNotificationTypes(models.IntegerChoices, Enum):
    ADD = 0, "Add"
    CHANGE = 1, "Change"
    CANCEL = 2, "Cancel"

# Create your models here.
class ShortNoticeNotification(models.Model):
    type = models.IntegerField(choices=ShortNoticeNotificationTypes.choices)
    #canceled time or rescheduled from time
    source_booking = models.OneToOneField(
        Booking, 
        null=True, 
        blank=True, 
        on_delete=models.PROTECT,
        related_name="short_notice_cancel"
    )
    #scheduled or rescheduled to
    target_booking = models.OneToOneField(
        Booking, 
        null=True, 
        blank=True, 
        on_delete=models.PROTECT,
        related_name="short_notice_schedule"
    )

    def __repr__(self):
        return ""
    
    @staticmethod
    def is_short_notice(instant: datetime.datetime):
        now = timezone.now()
        # Same day
        is_same_day = now.date() == instant.date()

        # After 6pm previous day
        after_close_previous_day = (
            ((instant.date() + datetime.timedelta(days=-1)) == now.date()) and
            now.time().hour >= 18
        )

        return is_same_day or after_close_previous_day