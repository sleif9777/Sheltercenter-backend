import datetime
from django.http import HttpRequest, JsonResponse
from rest_framework import status, viewsets
from rest_framework.decorators import action

from utils.DateTimeUtils import DateTimeUtils

from .models import AppointmentBase
from .serializers import AppointmentBaseSerializer

# Create your views here.
class AppointmentBaseViewSet(viewsets.ModelViewSet):
    queryset = AppointmentBase.objects.all().order_by("weekday", "time", "type")
    serializer_class = AppointmentBaseSerializer

    @action(detail=False, methods=["POST"], url_path="CreateTemplateAppointment")
    def CreateTemplateAppointment(self, request, *args, **kwargs):
        parsed_time: datetime.datetime = DateTimeUtils.Parse(
            request.data["time"], 
            "JSON", 
            isUTC=True
        )

        appointment_base = AppointmentBase.objects.create(
            weekday=request.data["weekday"],
            time=parsed_time.time(),
            type=request.data["type"],
            # subtype=(request.data["subtype"] if "subtype" in request.data else None)
        )

        return JsonResponse(
            AppointmentBaseSerializer(appointment_base).data, 
            status=status.HTTP_200_OK
        )

    @action(detail=False, methods=["GET"], url_path="GetAllTemplateAppointments")
    def GetAllTemplateAppointments(self, request: HttpRequest, *args, **kwargs):
        weekday = int(request.query_params["weekday"])
        appointment_bases = AppointmentBase.objects.filter(weekday=weekday)

        # TO DO: Make this closer to client's ITimeslot
        appointment_dict = {}
        for appointment in appointment_bases:
            serialized = AppointmentBaseSerializer(appointment).data
            time_str = str(appointment.time)
            if time_str not in appointment_dict:
                appointment_dict[time_str] = []
            appointment_dict[time_str].append(serialized)
        
        return JsonResponse(appointment_dict, status=status.HTTP_200_OK)   
    
    def get_queryset(self):
        params = self.process_query_params(self.request.query_params)

        if params:
            return AppointmentBase.objects.filter(**params)
        
        return AppointmentBase.objects.all()
    
    def process_query_params(self, query_params):
        params = dict(query_params)

        if 'weekday' in params.keys():
            params['weekday'] = int(params['weekday'][0])
            return params
        
        return None