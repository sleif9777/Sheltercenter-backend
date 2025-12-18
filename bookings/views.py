import datetime
import json
from django.http import HttpResponse
from rest_framework import status, viewsets

from appointments.serializers import AppointmentSerializer

from .models import Booking
from .serializers import BookingSerializer
from .services import BookingService

# Create your views here.
class BookingViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows users to be viewed or edited.
    """
    queryset = Booking.objects.all()
    serializer_class = BookingSerializer

    # def create(self, request, *args, **kwargs):
    #     try:
    #         match request.data["action"]:
    #             case "schedule":
    #                 updated_appointment = BookingService().schedule(request.data)
    #             case _:
    #                 pass

    #         return HttpResponse(
    #             AppointmentSerializer(updated_appointment).data,
    #             status=status.HTTP_201_CREATED,
    #             content_type="application/json"
    #         )
    #     except Exception as e:
    #         return HttpResponse(
    #             {
    #                 "message": e,
    #             },
    #             status=status.HTTP_400_BAD_REQUEST,
    #             content_type="application/json"
    #         )