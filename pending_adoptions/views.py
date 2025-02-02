
import datetime
from multiprocessing.managers import BaseManager
from django.http import HttpRequest, JsonResponse
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action

from appointments.enums import OutcomeTypes
from adopters.models import Adopter
from email_templates.views import EmailViewSet
from pending_adoption_updates.models import PendingAdoptionUpdate

from .enums import PendingAdoptionStatus
from .models import PendingAdoption
from .serializers import PendingAdoptionsSerializer

# Create your views here.
class PendingAdoptionViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows users to be viewed or edited.
    """
    queryset = PendingAdoption.objects.all()
    serializer_class = PendingAdoptionsSerializer

    @action(detail=False, methods=["GET"], url_path="GetAllPendingAdoptions")
    def GetAllPendingAdoptions(self, request: HttpRequest, *args, **kwargs):
        adoptions = PendingAdoption.objects.exclude(
            status=PendingAdoptionStatus.COMPLETED
        ).exclude(
            status=PendingAdoptionStatus.CANCELED
        )

        serialized = [PendingAdoptionsSerializer(adoption).data for adoption in adoptions]

        return JsonResponse({
            "adoptions": serialized
        })
    
    @action(detail=False, methods=["POST"], url_path="MarkStatus")
    def MarkStatus(self, request: HttpRequest, *args, **kwargs):
        id = request.data["id"]
        status = request.data["status"]
        heartworm = request.data["heartworm"]
        message = request.data["message"]
        pending_adoption = PendingAdoption.objects.get(pk=id)
        pending_adoption.mark_status(status, heartworm)

        if status == PendingAdoptionStatus.READY_TO_ROLL:
            EmailViewSet().ReadyToRoll(pending_adoption, message)

        if status == PendingAdoptionStatus.CANCELED:
            pending_adoption.source_appointment.outcome = OutcomeTypes.NO_DECISION
            pending_adoption.source_appointment.chosen_dog = ""
            pending_adoption.adopter.restrict_calendar(restrict=False)
            pending_adoption.source_appointment.save()

        return JsonResponse(
            PendingAdoptionsSerializer(pending_adoption).data,
        )
    
    @action(detail=False, methods=["POST"], url_path="CreatePendingAdoption")
    def CreatePendingAdoption(self, request: HttpRequest, *args, **kwargs):
        dog = request.data["dog"].title()
        adopter = Adopter.objects.get(pk=request.data["adopter"])
        circumstance = request.data["circumstance"]
        
        pending_adoption = PendingAdoption.objects.create(
            dog=dog,
            adopter=adopter,
            circumstance=circumstance,
            created_instant=timezone.now(),
            status=PendingAdoptionStatus.CHOSEN,
        )

        adopter.restrict_calendar()

        EmailViewSet().AdoptionCreated(pending_adoption)

        return JsonResponse(
            PendingAdoptionsSerializer(pending_adoption).data,
        )
    
    @action(detail=False, methods=["POST"], url_path="ChangeDog")
    def ChangeDog(self, request: HttpRequest, *args, **kwargs):
        adoption = PendingAdoption.objects.get(pk=request.data["adoptionID"])
        adoption.dog = request.data["newDog"]
        adoption.save()

        adoption.source_appointment.chosen_dog = adoption.dog
        adoption.source_appointment.save()

        return JsonResponse(
            PendingAdoptionsSerializer(adoption).data,
        )
    
    @action(detail=False, methods=["GET"], url_path="GetAllPendingAdoptionsAwaitingPaperwork")
    def GetAllPendingAdoptionsAwaitingPaperwork(self, request: HttpRequest, *args, **kwargs):
        adoptions = PendingAdoption.objects.filter(
            paperwork_appointment=None,
        )

        serialized = [PendingAdoptionsSerializer(adoption).data for adoption in adoptions]

        return JsonResponse({
            "adoptions": serialized
        })
    
    @action(detail=False, methods=["POST"], url_path="CreateUpdate")
    def CreateUpdate(self, request: HttpRequest, *args, **kwargs):
        adoption_id = request.data["adoptionID"]
        subject = request.data["subject"]
        message = request.data["message"]
        adoption = PendingAdoption.objects.get(pk=adoption_id)

        PendingAdoptionUpdate.objects.create(
            adoption=adoption
        )

        EmailViewSet().GenericMessage(adoption.adopter.user_profile, subject, message)

        return JsonResponse({
            "adoptions": PendingAdoptionsSerializer(adoption).data
        })
        
    