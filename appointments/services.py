import datetime

from adopters.models import Adopter
from appointment_bases.models import AppointmentBase
from short_notice_notifications.services import ShortNoticeNotificationsService
from bookings.models import Booking, BookingStatus
from short_notice_notifications.models import ShortNoticeNotification, ShortNoticeNotificationTypes
from utils.DateTimeUtils import DateTimeUtils

from .models import Appointment

class AppointmentsService():
    # @staticmethod
    def create_batch(self, date: datetime.datetime) -> list[Appointment]:
        """ Return a dictionary of appointments to be created for a date,
        using AppointmentBases to determine which weekday to copy from.
        """
        try:
            filtered_bases = AppointmentBase.objects.filter(weekday=date.weekday())
            batch_data = []
            for base in filtered_bases.iterator():
                appointment = Appointment(
                    type=base.type,
                    instant=base.get_instant_from_date(date)
                )

                batch_data.append(appointment)

            return batch_data
        except Exception:
            pass

    def Schedule(self, appointmentID: int, adopterID: int, instant: datetime):
        # 1. Create a new booking object with session data, attach appointment and adopter to booking
        appointment = Appointment.objects.get(pk=appointmentID)
        adopter = Adopter.objects.get(pk=adopterID)
        
        newBooking: Booking = Booking.objects.create(
            adopter=adopter, 
            appointment=appointment,
            status=BookingStatus.ACTIVE
        )

        # 2. Send email to the adopter
        MessagingService.CreateMessage(
            None, #template
            None, #send
            None, #recipient
            sendNow=True
        )

        # 3. If short notice, create a short notice notification
        if DateTimeUtils.IsShortNotice(appointment.instant):
            ShortNoticeNotificationsService.ShortNoticeSchedule(newBooking)

            shortNotice: ShortNoticeNotification = ShortNoticeNotification.objects.create(
                target_booking=newBooking,
                type=ShortNoticeNotificationTypes.ADD
            )

            shortNotice.NotifyAdoptions()
            
        # 3a. Email the short notice to adoptions

        # 4. Update the session


        #get appt id from kwargs
        #return a kwarg dict to update appointment with id of param kwarg and create a booking
        return ""

    def reschedule(self, **kwargs):
        #get appt id to schedule and cancel from kwargs
        #prepare update data for canceled appt and booking
        #prepare update data for scheduled appt and booking
        #process adopter
        return ""
