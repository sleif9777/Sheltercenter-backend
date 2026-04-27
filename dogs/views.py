import pytz

from adopters.views import AdopterViewSet
from datetime import date, datetime, timedelta
from django.db.models import Q
from django.http import JsonResponse
from django.utils import timezone
from environment_settings.models import EnvironmentSettings
from pending_adoptions.enums import PendingAdoptionStatus
from pending_adoptions.models import PendingAdoption
from pending_adoptions.serializers import DashboardPendingAdoptionDogSerializer
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
        today = timezone.localdate()
        monday = today - timedelta(days=today.weekday())

        # Convert monday to an aware datetime at midnight in the current timezone
        monday_aware = timezone.make_aware(datetime.combine(monday, datetime.min.time()))

        newly_in_home = Dog.objects.filter(
            status=DogStatus.HEALTHY_IN_HOME, last_updated__gte=monday_aware
        )

        fta = Dog.objects.filter(status=DogStatus.FTA)

        # Get dogs whose name matches a PendingAdoption with READY_TO_ROLL status
        ready_to_roll = PendingAdoption.objects.filter(status=PendingAdoptionStatus.READY_TO_ROLL)

        needs_sn = PendingAdoption.objects.filter(status=PendingAdoptionStatus.NEEDS_SN).difference(
            ready_to_roll
        )
        needs_wc = PendingAdoption.objects.filter(
            status=PendingAdoptionStatus.NEEDS_WELL_CHECK
        ).difference(ready_to_roll)

        return JsonResponse(
            {
                "hash": {
                    "chosen": {
                        "needsSN": [
                            DashboardPendingAdoptionDogSerializer(adoption).data
                            for adoption in needs_sn
                        ],
                        "needsWC": [
                            DashboardPendingAdoptionDogSerializer(adoption).data
                            for adoption in needs_wc
                        ],
                        "readyToRoll": [
                            DashboardPendingAdoptionDogSerializer(adoption).data
                            for adoption in ready_to_roll
                        ],
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

    @action(detail=False, methods=["GET"], url_path="GetDogSelectFieldOptions")
    def GetDogSelectFieldOptions(self, request):
        eastern = pytz.timezone("America/New_York")
        now = timezone.now()
        cutoff_end = eastern.localize(datetime(2026, 4, 29, 18, 0, 0))

        if now < cutoff_end:
            cutoff_start = date(2026, 4, 23)
        else:
            cutoff_start = now.astimezone(eastern).date() - timedelta(days=2)

        dogs = Dog.objects.filter(
            Q(status=DogStatus.AVAILABLE_NOW) | Q(last_updated__gte=cutoff_start)
        )

        options = [DogValueLabelPairSerializer(dog).data for dog in dogs]

        return JsonResponse({"options": options}, status=status.HTTP_200_OK)

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
