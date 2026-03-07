from adopters.views import AdopterViewSet
from appointments.enums import OutcomeTypes
from appointments.models import Appointment
from appointment_bases.enums import AppointmentTypes
from datetime import timedelta
from django.http import JsonResponse
from django.utils import timezone
from environment_settings.models import EnvironmentSettings
from pending_adoptions.enums import PendingAdoptionStatus
from pending_adoptions.models import PendingAdoption
from rest_framework import status, viewsets
from rest_framework.decorators import action

from .enums import DogStatus
from .models import Dog
from .serializers import *


# Create your views here.
class DogsViewSet(viewsets.ModelViewSet):
    queryset = Dog.objects.all()

    # Static methods
    @staticmethod
    def UnpackDogFromDogIDRequest(data) -> Dog:
        query = DogIDRequestSerializer(data=data)
        query.is_valid(raise_exception=True)

        dog_id: int = int(query.validated_data["dogID"])
        dog = Dog.objects.get(pk=dog_id)

        return dog

    # GET commands
    @action(detail=False, methods=["GET"], url_path="GetDashboardDogHash")
    def GetDashboardDogHash(self, request):
        # Get start of current week (Monday)
        today = timezone.localdate()
        monday = today - timedelta(days=today.weekday())

        # Get dog names from adoption and paperwork appointments since Monday
        adoption_appts_this_week = Appointment.objects.filter(
            instant__date__gte=monday,
            outcome=OutcomeTypes.ADOPTION,
            soft_deleted=False,
        )
        paperwork_appts_this_week = Appointment.objects.filter(
            instant__date__gte=monday,
            type=AppointmentTypes.PAPERWORK,
            soft_deleted=False,
        )

        adopted_dog_names = set(adoption_appts_this_week.values_list("chosen_dog", flat=True))
        paperwork_dog_names = set(
            PendingAdoption.objects.filter(
                paperwork_appointment__in=paperwork_appts_this_week
            ).values_list("dog", flat=True)
        )

        newly_in_home = Dog.objects.filter(
            status=DogStatus.HEALTHY_IN_HOME,
            name__in=adopted_dog_names | paperwork_dog_names,
        )
        fta = Dog.objects.filter(status=DogStatus.FTA)

        # Get dogs whose name matches a PendingAdoption with READY_TO_ROLL status
        ready_to_roll_dog_names = PendingAdoption.objects.filter(
            status=PendingAdoptionStatus.READY_TO_ROLL
        ).values_list("dog", flat=True)
        ready_to_roll = Dog.objects.filter(name__in=ready_to_roll_dog_names)
        
        needs_sn = Dog.objects.filter(status=DogStatus.CHOSEN_SN).difference(ready_to_roll)
        needs_wc = Dog.objects.filter(status=DogStatus.CHOSEN_WC).difference(ready_to_roll)

        return JsonResponse(
            {
                "hash": {
                    "chosen": {
                        "needsSN": [DashboardDogSerializer(dog).data for dog in needs_sn],
                        "needsWC": [DashboardDogSerializer(dog).data for dog in needs_wc],
                        "readyToRoll": [DashboardDogSerializer(dog).data for dog in ready_to_roll],
                    },
                    "fta": [DashboardDogSerializer(dog).data for dog in fta],
                    "newlyInHome": [DashboardDogSerializer(dog).data for dog in newly_in_home],
                }
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=False, methods=["GET"], url_path="GetDogDemographics")
    def GetDogDemographics(self, request):
        dog = DogsViewSet.UnpackDogFromDogIDRequest(request.query_params)

        return JsonResponse({"dog": DogDemographicsSerializer(dog).data}, status=status.HTTP_200_OK)

    @action(detail=False, methods=["GET"], url_path="GetPublishableDogs")
    def GetPublishableDogs(self, request):
        environment = EnvironmentSettings.objects.get(pk=1)
        publishable_dogs = Dog.objects.filter(publishable=True)

        available_ids = [
            HashDogSerializer(dog).data for dog in publishable_dogs.intersection(publishable_dogs)
        ]

        hash = {
            "watching": {"available": [], "notAvailable": []},
            "notWatching": available_ids,
        }

        return JsonResponse(
            {"hash": hash, "lastImport": environment.last_dog_import_iso}, status=status.HTTP_200_OK
        )

    @action(detail=False, methods=["GET"], url_path="GetWatchlistForAdopter")
    def GetWatchlistForAdopter(self, request):
        adopter = AdopterViewSet.UnpackAdopterFromAdopterIDRequest(request.query_params)
        environment = EnvironmentSettings.objects.get(pk=1)

        publishable_dogs = Dog.objects.filter(publishable=True)
        watchlist_dogs = Dog.objects.filter(interest_adopters__pk=adopter.id)

        watchlist_dogs = [
            WatchlistDogSerializer(dog).data
            for dog in publishable_dogs.intersection(watchlist_dogs)
            if dog.publishable
        ]

        return JsonResponse(
            {"watchlist": watchlist_dogs, "lastImport": environment.last_dog_import_iso},
            status=status.HTTP_200_OK,
        )

    @action(detail=False, methods=["GET"], url_path="GetWatchlistHashForAdopter")
    def GetWatchlistHashForAdopter(self, request):
        adopter = AdopterViewSet.UnpackAdopterFromAdopterIDRequest(request.query_params)
        environment = EnvironmentSettings.objects.get(pk=1)

        publishable_dogs = Dog.objects.filter(publishable=True)
        watchlist_dogs = Dog.objects.filter(interest_adopters__pk=adopter.id)

        available_ids = [
            HashDogSerializer(dog).data for dog in publishable_dogs.intersection(watchlist_dogs)
        ]
        not_available_ids = [
            HashDogSerializer(dog).data for dog in watchlist_dogs.difference(publishable_dogs)
        ]
        not_watching_ids = [
            HashDogSerializer(dog).data for dog in publishable_dogs.difference(watchlist_dogs)
        ]

        hash = {
            "watching": {"available": available_ids, "notAvailable": not_available_ids},
            "notWatching": not_watching_ids,
        }

        return JsonResponse(
            {"hash": hash, "lastImport": environment.last_dog_import_iso}, status=status.HTTP_200_OK
        )

    # POST commands
    @action(detail=False, methods=["POST"], url_path="AddDogToList")
    def AddDogToList(self, request: ListModificationRequest):
        adopter = AdopterViewSet.UnpackAdopterFromAdopterIDRequest(request.data)
        dog = DogsViewSet.UnpackDogFromDogIDRequest(request.data)

        if not dog.interest_adopters.contains(adopter):
            dog.interest_adopters.add(adopter)
            dog.save()

        return JsonResponse({}, status=status.HTTP_200_OK)

    @action(detail=False, methods=["POST"], url_path="RemoveDogFromList")
    def RemoveDogFromList(self, request: ListModificationRequest):
        adopter = AdopterViewSet.UnpackAdopterFromAdopterIDRequest(request.data)
        dog = DogsViewSet.UnpackDogFromDogIDRequest(request.data)

        if dog.interest_adopters.contains(adopter):
            dog.interest_adopters.remove(adopter)
            dog.save()

        return JsonResponse({}, status=status.HTTP_200_OK)
