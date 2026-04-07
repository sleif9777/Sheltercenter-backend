import datetime
import traceback

from django.db.models import CharField, Value
from django.db.models.functions import Concat
from django.http import JsonResponse
from django.utils import timezone
from appointments.models import Appointment
from appointments.views import AppointmentViewSet
from email_templates.views import EmailViewSet
from rest_framework import status, viewsets
from rest_framework.decorators import action
from users.models import UserProfile
from utils import DateTimeUtils

from .enums import ApprovalStatus
from .models import Adopter
from .serializers import *


# Create your views here.
class AdopterViewSet(viewsets.ModelViewSet):
    queryset = Adopter.objects.all()

    # Static methods
    @staticmethod
    def UnpackAdopterFromAdopterIDRequest(data) -> Adopter:
        query = AdopterIDRequestSerializer(data=data)
        query.is_valid(raise_exception=True)

        adopter_id: int = int(query.validated_data["adopterID"])
        adopter = Adopter.objects.get(pk=adopter_id)

        return adopter

    # GET commands

    @action(detail=False, methods=["GET"], url_path="GetAdopterAlerts")
    def GetAdopterAlerts(self, request):
        date, _ = AppointmentViewSet.GetISODateFromISODateRequest(request.query_params)

        appts = Appointment.objects.filter(
            instant__range=DateTimeUtils.get_range_for_date(date), soft_deleted=False
        )

        alert_dict = []
        seen_adopter_ids = set()

        for appt in appts:
            if not appt.has_current_booking:
                continue

            adopter: Adopter = appt.get_current_booking().adopter

            # Skip if we've already processed this adopter
            if adopter.id in seen_adopter_ids:
                continue

            seen_adopter_ids.add(adopter.id)

            history = adopter.booking_history
            alerts = []

            if history["noShow"] > 1:
                alerts.append("{0} no shows".format(history["noShow"]))

            if history["noDecision"] > 1:
                alerts.append("{0} no decisions".format(history["noDecision"]))

            if len(alerts) > 0:
                alert_dict.append({"name": adopter.user_profile.full_name, "alerts": alerts})

        return JsonResponse(
            {
                "alerts": alert_dict,
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=False, methods=["GET"], url_path="GetAdopterDemographics")
    def GetAdopterDemographics(self, request):
        adopter = AdopterViewSet.UnpackAdopterFromAdopterIDRequest(request.query_params)
        appt = adopter.get_current_appointment()

        serializer = AdopterDemographicsSerializer(adopter)

        return JsonResponse(
            {
                "demo": serializer.data,
                "apptID": appt.id if appt else None,
            }
        )

    @action(detail=False, methods=["GET"], url_path="GetAdopterDirectoryListing")
    def GetAdopterDirectoryListing(self, request):
        query = AdopterDirectoryListingRequestSerializer(data=request.query_params)
        query.is_valid(raise_exception=True)

        filter_text: str = query.validated_data.get("filterText", "").strip().lower()
        include_archived: bool = query.validated_data["includeArchived"]

        if not filter_text:
            return JsonResponse({"adopters": []}, status=status.HTTP_200_OK)

        try:
            UserProfile.remove_faulty()
            adopters = (
                Adopter.objects.filter(approved_until__gte=DateTimeUtils.get_today())
                .select_related("user_profile")
                .annotate(
                    disambiguated_name=Concat(
                        "user_profile__first_name",
                        Value(" "),
                        "user_profile__last_name",
                        Value(" ("),
                        "user_profile__primary_email",
                        Value(")"),
                        output_field=CharField(),
                    )
                )
                .filter(disambiguated_name__icontains=filter_text)
            )

            if not include_archived:
                adopters = adopters.filter(user_profile__archived=False)

            serialized = [DirectoryAdopterSerializer(adopter).data for adopter in adopters]

            return JsonResponse({"adopters": serialized}, status=status.HTTP_200_OK)
        except:
            traceback.print_exc()

    @action(detail=False, methods=["GET"], url_path="GetAdopterPreferences")
    def GetAdopterPreferences(self, request):
        adopter = AdopterViewSet.UnpackAdopterFromAdopterIDRequest(request.query_params)
        serializer = AdopterPreferencesResponseSerializer(adopter)

        return JsonResponse({"pref": serializer.data}, status=status.HTTP_200_OK)

    @action(detail=False, methods=["GET"], url_path="GetAdopterSelectFieldOptions")
    def GetAdopterSelectFieldOptions(self, request):
        print(request.query_params)
        include_scheduled = request.query_params["includeScheduled"].lower() == "true"
        include_archived = request.query_params["includeArchived"].lower() == "true"

        adopters = Adopter.objects.filter(
            approved_until__gte=DateTimeUtils.get_today(),
            status=ApprovalStatus.APPROVED,
        )

        options = [
            AdopterValueLabelPairSerializer(adopter).data
            for adopter in adopters
            if (
                (include_scheduled or not adopter.has_current_booking)
                and (include_archived or not adopter.user_profile.archived)
                and not adopter.user_profile.adoption_completed
            )
        ]

        print(
            include_archived,
            include_scheduled,
            [
                adopter
                for adopter in adopters
                if (
                    (include_scheduled or not adopter.has_current_booking)
                    and (include_archived or not adopter.user_profile.archived)
                    and not adopter.user_profile.adoption_completed
                )
            ],
        )

        return JsonResponse({"options": options}, status=status.HTTP_200_OK)

    @action(detail=False, methods=["GET"], url_path="GetRecentlyUploadedAdopters")
    def GetRecentlyUploadedAdopters(self, request):
        query = RecentlyUploadedAdoptersRequestSerializer(data=request.query_params)
        query.is_valid(raise_exception=True)

        lookback_days: int = query.validated_data["lookbackDays"]

        lookback_cutoff = timezone.now() - datetime.timedelta(days=lookback_days)

        adopters = Adopter.objects.filter(
            last_uploaded__gte=lookback_cutoff,
            user_profile__archived=False,
        )

        serializer = RecentlyUploadedAdoptersResponseSerializer(adopters, many=True)

        return JsonResponse({"adopters": serializer.data})

    # POST commands

    @action(detail=False, methods=["POST"], url_path="MessageAdopter")
    def MessageAdopter(self, request):
        query = SendMessageRequestSerializer(data=request.data)
        query.is_valid(raise_exception=True)

        adopter_id: int = int(query.validated_data["adopterID"])
        adopter = Adopter.objects.get(pk=adopter_id)

        subject: str = query.validated_data["subject"]
        message: str = query.validated_data["message"]

        EmailViewSet().GenericMessage(adopter.user_profile, subject, message)

        return JsonResponse({}, status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=["POST"], url_path="MessageAdoptions")
    def MessageAdoptions(self, request):
        query = SendMessageRequestSerializer(data=request.data)
        query.is_valid(raise_exception=True)

        adopter_id: int = int(query.validated_data["adopterID"])
        adopter = Adopter.objects.get(pk=adopter_id)

        subject: str = "Message from " + adopter.user_profile.full_name
        message: str = query.validated_data["message"]

        EmailViewSet().GenericMessage(adopter.user_profile, subject, message, to_adoptions=True)

        return JsonResponse({}, status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=["POST"], url_path="ResendApproval")
    def ResendApproval(self, request):
        adopter = self.UnpackAdopterFromAdopterIDRequest(request.data)

        EmailViewSet().ApplicationApproved(adopter)

        return JsonResponse({}, status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=["POST"], url_path="RestoreCalendarAccess")
    def RestoreCalendarAccess(self, request):
        adopter = self.UnpackAdopterFromAdopterIDRequest(request.data)

        adopter.restrict_calendar(restrict=False)

        return JsonResponse({}, status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=["POST"], url_path="UpdateAdopterPreferences")
    def UpdateAdopterPreferences(self, request):
        query = AdopterPreferencesRequestSerializer(data=request.data)
        query.is_valid(raise_exception=True)

        adopter_id: int = int(query.validated_data["adopterID"])
        adopter = Adopter.objects.get(pk=adopter_id)

        adopter.update_preferences(query.validated_data)

        return JsonResponse({}, status=status.HTTP_200_OK)
