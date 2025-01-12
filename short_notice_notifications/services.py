from messaging.services import MessagingService
from .models import ShortNoticeNotification, ShortNoticeNotificationTypes
from bookings.models import Booking

class ShortNoticeNotificationsService:
    def ShortNoticeSchedule(newBooking: Booking):
        shortNotice: ShortNoticeNotification = ShortNoticeNotification.objects.create(
            target_booking=newBooking,
            type=ShortNoticeNotificationTypes.ADD
        )

    def NotifyAdoptions(shortNotice: ShortNoticeNotification):
        MessagesService.CreateMessage(
            None, #template
            None, #sender (autosystem)
            None, #recipient (adoptions)
            sendNow=True,
        )