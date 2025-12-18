from adopters.models import Adopter
from appointments.models import Appointment
from .models import Booking, BookingStatus

class BookingService():
    def get_booking_history_for_adopter(self, adopter_id: int):
        adopter = Adopter.objects.get(pk=adopter_id)
        return Booking.objects.filter(adopter=adopter)
    
    @staticmethod
    def schedule(data):
        new_booking = Booking.objects.create(
            adopter=Adopter.objects.get(pk=data["adopter_id"]),
            status=BookingStatus.ACTIVE,
        )

        appointment = Appointment.objects.get(pk=data["appt_id"])
        appointment.booking = new_booking
        appointment.save()

        return appointment