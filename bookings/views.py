from rest_framework import viewsets

from .models import Booking


# Create your views here.
class BookingViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows users to be viewed or edited.
    """
    queryset = Booking.objects.all()
