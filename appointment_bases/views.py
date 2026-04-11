import datetime

from django.http import JsonResponse
from rest_framework import status, viewsets
from rest_framework.decorators import action, permission_classes

from auth.security import IsStaffUser

from .mapper import TemplateHashMapper
from .models import AppointmentBase
from .serializers import *


# Create your views here.
class AppointmentBaseViewSet(viewsets.ModelViewSet):
    queryset = AppointmentBase.objects.all().order_by("weekday", "time", "type")
    serializer_class = AppointmentBaseSerializer

    # GET commands
    @action(detail=False, methods=["GET"], url_path="GetTemplatesForWeekday", permission_classes=[IsStaffUser])
    def GetTemplatesForWeekday(self, request):
        query = WeekdayRequestSerializer(data=request.query_params)
        query.is_valid(raise_exception=True)

        weekday = query.validated_data["weekday"]
        templates = AppointmentBase.objects.filter(weekday=weekday)

        template_hash = (
            TemplateHashMapper.map_templates(templates) if templates.count() > 0 else None
        )

        return JsonResponse({"templateHash": template_hash}, status=status.HTTP_200_OK)

    # POST commands
    @action(detail=False, methods=["POST"], url_path="CreateTemplateAppointment", permission_classes=[IsStaffUser])
    def CreateTemplateAppointment(self, request):
        query = CreateTemplateAppointmentRequestSerializer(data=request.data)
        query.is_valid(raise_exception=True)

        hour: int = query.validated_data["hour"]
        minute: int = query.validated_data["minute"]
        weekday: int = query.validated_data["weekday"]
        type: int = query.validated_data["type"]

        const_time = datetime.time(hour=hour, minute=minute)

        AppointmentBase.objects.create(
            time=const_time,
            weekday=weekday,
            type=type,
        )

        return JsonResponse({}, status=status.HTTP_201_CREATED)
