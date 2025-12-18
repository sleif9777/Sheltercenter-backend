import datetime
import traceback
from django.http import HttpRequest, JsonResponse
from rest_framework import status, viewsets
from rest_framework.decorators import action

from appointments.serializers import AppointmentSerializer
from email_templates.views import EmailViewSet
from users.models import UserProfile
from utils.DateTimeUtils import DateTimeUtils

from .models import Adopter, AdopterStatuses
from .serializers import *

# Create your views here.
class AdopterViewSet(viewsets.ModelViewSet):
    queryset = Adopter.objects.all()
    serializer_class = AdopterSerializer

    @action(detail=False, methods=["GET"], url_path="GetAllAdopters")
    def GetAllAdopters(self, request: HttpRequest):
        try:
            UserProfile.remove_faulty()
            adopters = Adopter.objects.filter(
                approved_until__gte=DateTimeUtils.GetToday(),
                user_profile__archived=False
            )

            serialized = [AdopterBaseSerializer(adopter).data for adopter in adopters]
            
            return JsonResponse(
                {"adopters": serialized}
            )  
        except Exception as e:
            print(e)
            traceback.print_exc()

    @action(detail=False, methods=["GET"], url_path="GetAdoptersForBooking")
    def GetAdoptersForBooking(self, request: HttpRequest):
        UserProfile.remove_faulty()
        adopters = Adopter.objects.filter(
            approved_until__gte=DateTimeUtils.GetToday(),
            status=AdopterStatuses.APPROVED,
            user_profile__archived=False
        )

        if "includeAdopter" in request.data:
            include_adopter = Adopter.objects.get(pk=request.data["includeAdopter"])
            adopters |= include_adopter

        for adopter in adopters:
            if adopter.user_profile == None:
                profile = UserProfile()

        serialized = [AdopterBaseSerializer(adopter).data for adopter in adopters if not adopter.has_current_booking]
        
        return JsonResponse(
            {"adopters": serialized}
        ) 

    @action(detail=False, methods=["GET"], url_path="GetAdopterDetail")
    def GetAdopterDetail(self, request: HttpRequest):
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

    
    @action(detail=False, methods=["GET"], url_path="GetRecentlyUploadedAdopters")
    def GetRecentlyUploadedAdopters(self, request: HttpRequest):
        lookback_days = int(request.query_params["lookbackDays"])
        lookback_cutoff = DateTimeUtils.GetToday() - datetime.timedelta(days=lookback_days)
        print(lookback_cutoff)

        adopters = Adopter.objects.filter(
            last_uploaded__gte=lookback_cutoff,
            user_profile__archived=False
        )

        serialized = [AdopterBaseSerializer(adopter).data for adopter in adopters if not adopter.has_current_booking]
        print(serialized)
        
        return JsonResponse(
            {"adopters": serialized}
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
    
    @action(detail=False, methods=["POST"], url_path="RestoreCalendarAccess")
    def RestoreCalendarAccess(self, request):
        adopter_id = request.data["adopterID"]
        adopter = Adopter.objects.get(pk=adopter_id)
        adopter.restrict_calendar(restrict=False)

        return JsonResponse(
            {},
            status=status.HTTP_200_OK
        )