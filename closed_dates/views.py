from django.http import JsonResponse
from rest_framework import status, viewsets
from rest_framework.decorators import action

from closed_dates.models import ClosedDate
from utils.DateTimeUtils import DateTimeUtils

from .serializers import ClosedDateSerializer

# Create your views here.
class ClosedDateViewSet(viewsets.ModelViewSet):
    queryset = ClosedDate.objects.all().order_by("date")
    serializer_class = ClosedDateSerializer

    @action(detail=False, methods=["POST"], url_path="MarkDateAsClosed")
    def MarkDateAsClosed(self, request, *args, **kwargs):
        date = DateTimeUtils.Parse(request.data["date"], "JSON", isUTC=True).date()
        
        closed_date = ClosedDate.objects.create(date=date)

        return JsonResponse({ "closedDate": ClosedDateSerializer(closed_date).data }, status=status.HTTP_201_CREATED)