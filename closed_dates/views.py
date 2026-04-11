from appointments.views import AppointmentViewSet
from closed_dates.models import ClosedDate
from django.http import JsonResponse
from rest_framework import status, viewsets
from rest_framework.decorators import action, permission_classes

from auth.security import IsStaffUser

from .serializers import ClosedDateSerializer


# Create your views here.
class ClosedDateViewSet(viewsets.ModelViewSet):
    queryset = ClosedDate.objects.all().order_by("date")
    serializer_class = ClosedDateSerializer

    @action(detail=False, methods=["POST"], url_path="MarkDateAsClosed", permission_classes=[IsStaffUser])
    def MarkDateAsClosed(self, request, *args, **kwargs):
        date_obj, _ = AppointmentViewSet.GetISODateFromISODateRequest(request.data)
        closed_date = ClosedDate.objects.create(date=date_obj)

        return JsonResponse(
            {"closedDate": ClosedDateSerializer(closed_date).data}, status=status.HTTP_201_CREATED
        )

    @action(detail=False, methods=["POST"], url_path="UndoMarkDateAsClosed", permission_classes=[IsStaffUser])
    def UndoMarkDateAsClosed(self, request, *args, **kwargs):
        date_obj, _ = AppointmentViewSet.GetISODateFromISODateRequest(request.data)
        closed_date = ClosedDate.objects.get(date=date_obj)

        closed_date.delete()

        return JsonResponse({}, status=status.HTTP_200_OK)
