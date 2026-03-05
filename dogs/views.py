from adopters.views import AdopterViewSet
from django.http import JsonResponse
from environment_settings.models import EnvironmentSettings
from rest_framework import status, viewsets
from rest_framework.decorators import action

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
    @action(detail=False, methods=["GET"], url_path="GetDogDemographics")
    def GetDogDemographics(self, request):
        dog = DogsViewSet.UnpackDogFromDogIDRequest(request.query_params)

        return JsonResponse({"dog": DogDemographicsSerializer(dog).data}, status=status.HTTP_200_OK)

    @action(detail=False, methods=["GET"], url_path="GetPublishableDogs")
    def GetPublishableDogs(self, request):
        environment = EnvironmentSettings.objects.get(pk=1)        
        publishable_dogs = Dog.objects.filter(available_now=True)

        available_ids = [
            HashDogSerializer(dog).data for dog in publishable_dogs.intersection(publishable_dogs)
        ]

        hash = {
            "watching": {"available": [], "notAvailable": []},
            "notWatching": available_ids,
        }

        return JsonResponse({"hash": hash, "lastImport": environment.last_dog_import_iso}, status=status.HTTP_200_OK)

    @action(detail=False, methods=["GET"], url_path="GetWatchlistForAdopter")
    def GetWatchlistForAdopter(self, request):
        adopter = AdopterViewSet.UnpackAdopterFromAdopterIDRequest(request.query_params)
        environment = EnvironmentSettings.objects.get(pk=1)
        
        publishable_dogs = Dog.objects.filter(available_now=True)
        watchlist_dogs = Dog.objects.filter(interest_adopters__pk=adopter.id)

        watchlist_dogs = [
            WatchlistDogSerializer(dog).data for dog in publishable_dogs.intersection(watchlist_dogs) if dog.available_now
        ]

        return JsonResponse({"watchlist": watchlist_dogs, "lastImport": environment.last_dog_import_iso}, status=status.HTTP_200_OK)

    @action(detail=False, methods=["GET"], url_path="GetWatchlistHashForAdopter")
    def GetWatchlistHashForAdopter(self, request):
        adopter = AdopterViewSet.UnpackAdopterFromAdopterIDRequest(request.query_params)
        environment = EnvironmentSettings.objects.get(pk=1)
        
        publishable_dogs = Dog.objects.filter(available_now=True)
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

        return JsonResponse({"hash": hash, "lastImport": environment.last_dog_import_iso}, status=status.HTTP_200_OK)

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
