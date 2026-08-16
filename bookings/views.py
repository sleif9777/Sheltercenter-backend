from rest_framework import viewsets
from users.enums import SecurityLevel

from .models import Booking


# Create your views here.
class BookingViewSet(viewsets.ModelViewSet):
    queryset = Booking.objects.all()

    def get_queryset(self):
        if self.request.user.security_level < SecurityLevel.GREETER:
            return Booking.objects.filter(adopter=self.request.user.adopter_profile)
        return Booking.objects.all()
