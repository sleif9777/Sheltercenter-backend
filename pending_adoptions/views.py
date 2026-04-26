from adopters.models import Adopter
from appointments.enums import OutcomeTypes
from django.http import JsonResponse
from django.utils import timezone
from adopters.views import AdopterViewSet
from dogs.models import Dog
from email_templates.views import EmailViewSet
from pending_adoption_updates.models import PendingAdoptionUpdate
from rest_framework import status, viewsets
from rest_framework.decorators import action

from .enums import PendingAdoptionStatus
from .models import PendingAdoption
from .serializers import *


# Create your views here.
class PendingAdoptionViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows users to be viewed or edited.
    """

    queryset = PendingAdoption.objects.all()
    serializer_class = PendingAdoptionsSerializer

    # Static methods
    @staticmethod
    def UnpackAdopterFromAdopterIDRequest(request) -> Adopter:
        query = AdoptionIDRequestSerializer(data=request.query_params)
        query.is_valid(raise_exception=True)

        adoption_id: int = int(query.validated_data["adoptionID"])
        adoption = Adopter.objects.get(pk=adoption_id)

        return adoption

    # GET commands
    @action(detail=False, methods=["GET"], url_path="GetActivePendingAdoptions")
    def GetActivePendingAdoptions(self, request):
        adoptions = PendingAdoption.objects.exclude(
            status=PendingAdoptionStatus.CANCELED,
        ).exclude(
            status=PendingAdoptionStatus.COMPLETED,
        )

        serialized = [PendingAdoptionsSerializer(adoption).data for adoption in adoptions]

        return JsonResponse({"adoptions": serialized})

    @action(detail=False, methods=["GET"], url_path="GetPendingAdoptionSelectFieldOptions")
    def GetPendingAdoptionSelectFieldOptions(self, request):
        adoptions = (
            PendingAdoption.objects.filter(
                paperwork_appointment=None,
            )
            .exclude(
                status=PendingAdoptionStatus.CANCELED,
            )
            .exclude(
                status=PendingAdoptionStatus.COMPLETED,
            )
        )

        options = [PendingAdoptionValueLabelPairSerializer(adoption).data for adoption in adoptions]

        return JsonResponse({"adoptions": options}, status=status.HTTP_200_OK)

    # POST commands
    @action(detail=False, methods=["POST"], url_path="AddUpdate")
    def AddUpdate(self, request):
        query = CreatePendingAdoptionUpdateRequestSerializer(data=request.data)
        query.is_valid(raise_exception=True)

        subject = query.validated_data["subject"]
        message = query.validated_data["message"]

        adoption = query.get_adoption()
        PendingAdoptionUpdate.objects.create(adoption=adoption)

        EmailViewSet().GenericMessage(adoption.adopter.user_profile, subject, message)

        return JsonResponse(status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["POST"], url_path="ChangeDog")
    def ChangeDog(self, request):
        query = ChangeDogRequestSerializer(data=request.data)
        query.is_valid(raise_exception=True)
        adoption = query.get_adoption()

        adoption.dog = query.validated_data["newDog"]
        adoption.save()

        adoption.source_appointment.chosen_dog = adoption.dog
        adoption.source_appointment.save()

        return JsonResponse(
            PendingAdoptionsSerializer(adoption).data,
        )

    @action(detail=False, methods=["POST"], url_path="CreatePendingAdoption")
    def CreatePendingAdoption(self, request):
        adopter = AdopterViewSet.UnpackAdopterFromAdopterIDRequest(request.data)

        query = CreatePendingAdoptionRequestSerializer(data=request.data)
        query.is_valid(raise_exception=True)

        if "dog" in query.validated_data:
            dogID = None
            dog = query.validated_data["dog"].title()
        elif "dogID" in query.validated_data:
            dogID = int(query.validated_data["dogID"])
            dog = Dog.objects.get(pk=dogID).name

        circumstance = query.validated_data["circumstance"]

        pending_adoption = PendingAdoption.objects.create(
            dog=dog,
            dogID=dogID,
            adopter=adopter,
            circumstance=circumstance,
            created_instant=timezone.now(),
            status=PendingAdoptionStatus.CHOSEN,
        )

        adopter.restrict_calendar()

        EmailViewSet().AdoptionCreated(pending_adoption)

        return JsonResponse({}, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["POST"], url_path="MarkHeartworm")
    def MarkHeartworm(self, request):
        query = MarkHeartwormRequestSerializer(data=request.data)
        query.is_valid(raise_exception=True)

        new_hw = query.validated_data["heartworm"]

        adoption = query.get_adoption()
        adoption.mark_hw(new_hw)

        return JsonResponse({}, status=status.HTTP_200_OK)

    @action(detail=False, methods=["POST"], url_path="MarkStatus")
    def MarkStatus(self, request):
        query = MarkStatusRequestSerializer(data=request.data)
        query.is_valid(raise_exception=True)

        new_status = query.validated_data["status"]
        message = query.validated_data.get("message", "")

        adoption = query.get_adoption()
        adoption.mark_status(new_status)

        if new_status == PendingAdoptionStatus.READY_TO_ROLL:
            EmailViewSet().ReadyToRoll(adoption, message)

        if new_status == PendingAdoptionStatus.CANCELED and adoption.source_appointment:
            if adoption.status != PendingAdoptionStatus.COMPLETED:
                adoption.adopter.restrict_calendar(restrict=False)
            adoption.source_appointment.outcome = OutcomeTypes.NO_DECISION
            adoption.source_appointment.chosen_dog = ""
            adoption.source_appointment.save()

        return JsonResponse({}, status=status.HTTP_200_OK)
