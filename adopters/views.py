from django.http import HttpRequest, JsonResponse
from rest_framework import status, viewsets
from rest_framework.decorators import action

from appointments.serializers import AppointmentSerializer
from bookings.serializers import BookingSerializer
from email_templates.views import EmailViewSet
from utils.DateTimeUtils import DateTimeUtils

from .models import Adopter, AdopterStatuses
from .serializers import *
from .services import AdopterService


# Create your views here.
class AdopterViewSet(viewsets.ModelViewSet):
    # permission_classes = [permissions.IsAuthenticated]
    queryset = Adopter.objects.all()
    serializer_class = AdopterSerializer
    service = AdopterService()
    
    @action(detail=False, methods=["GET"], url_path="GetAllAdopters")
    def GetAllAdopters(self, request: HttpRequest, *args, **kwargs):
        adopters = Adopter.objects.filter(approved_until__gte=DateTimeUtils.GetToday())

        serialized = [AdopterSerializer(adopter).data for adopter in adopters]
        
        return JsonResponse(
            {"adopters": serialized}
        )  

    @action(detail=False, methods=["GET"], url_path="GetAdoptersForBooking")
    def GetAdoptersForBooking(self, request: HttpRequest, *args, **kwargs):
        adopters = Adopter.objects.filter(
            approved_until__gte=DateTimeUtils.GetToday(),
            status=AdopterStatuses.APPROVED,
        )

        if "includeAdopter" in request.data:
            include_adopter = Adopter.objects.get(pk=request.data["includeAdopter"])
            adopters |= include_adopter

        serialized = [AdopterSerializer(adopter).data for adopter in adopters if not adopter.has_current_booking]
        
        return JsonResponse(
            {"adopters": serialized}
        ) 

    @action(detail=False, methods=["GET"], url_path="GetAdopterDetail")
    def GetAdopterDetail(self, request: HttpRequest, *args, **kwargs):
        adopter_id = int(request.query_params["forAdopter"])
        adopter = Adopter.objects.get(pk=adopter_id)
        appointment = adopter.get_current_appointment()
        
        return JsonResponse(
            {
                "adopter": AdopterSerializer(adopter).data,
                "currentAppointment": AppointmentSerializer(appointment).data if appointment else None,
                "bookingHistory": adopter.booking_history
            }
        )  

    @action(detail=False, methods=["POST"], url_path="MessageAdopter")
    def MessageAdopter(self, request):
        adopter_id = request.data["adopterID"]
        subject = request.data["subject"]
        message = request.data["message"]
        adopter = Adopter.objects.get(pk=adopter_id)

        EmailViewSet().GenericMessage(adopter.user_profile, subject, message)

        return JsonResponse(
            {},
            status=status.HTTP_200_OK
        )  
    
    @action(detail=False, methods=["POST"], url_path="ResendApproval")
    def ResendApproval(self, request):
        adopter_id = request.data["adopterID"]
        adopter = Adopter.objects.get(pk=adopter_id)

        EmailViewSet().ApplicationApproved(adopter)

        return JsonResponse(
            {},
            status=status.HTTP_200_OK
        )