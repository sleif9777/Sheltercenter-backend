from rest_framework import serializers
from dogs.models import Dog
from dogs.enums import DogSex

from adopters.serializers import AdopterIDRequestSerializer


class DogIDRequestSerializer(serializers.Serializer):
    dogID = serializers.IntegerField()

    def validate_dogID(self, value: int) -> int:
        if not Dog.objects.filter(pk=int(value)).exists():
            raise serializers.ValidationError("Dog does not exist.")
        return value


class ListModificationRequest(DogIDRequestSerializer, AdopterIDRequestSerializer):
    pass


class DashboardDogSerializer(serializers.ModelSerializer):
    ID = serializers.IntegerField(source="id")
    name = serializers.CharField()
    photoURL = serializers.CharField(source="photo_url")
    unavailableDate = serializers.CharField(source="unavailable_date_iso", allow_null=True)

    class Meta:
        model = Dog
        fields = ["ID", "name", "photoURL", "unavailableDate"]


class DogSerializerBase(serializers.ModelSerializer):
    ID = serializers.IntegerField(source="id")
    name = serializers.CharField()
    ageMonths = serializers.IntegerField(source="age_months")

    class Meta:
        model = Dog
        fields = ["ID", "name", "ageMonths"]


class HashDogSerializer(DogSerializerBase):
    interestCount = serializers.IntegerField(source="interest_count")
    weight = serializers.IntegerField()

    class Meta:
        model = Dog
        fields = [
            "ID",
            "name",
            "ageMonths",
            "interestCount",
            "weight",
        ]


class WatchlistDogSerializer(DogSerializerBase):
    availableNow = serializers.BooleanField(source="publishable")
    availableDate = serializers.CharField(source="available_date_iso", allow_null=True)
    funSize = serializers.BooleanField(source="fun_size")

    class Meta:
        model = Dog
        fields = [
            "ID",
            "name",
            "ageMonths",
            "funSize",
            "availableNow",
            "availableDate",
        ]


class DogDemographicsSerializer(HashDogSerializer, WatchlistDogSerializer):
    shelterluvID = serializers.IntegerField(source="shelterluv_id")
    description = serializers.CharField()
    photoURL = serializers.CharField(source="photo_url")
    sex = serializers.ChoiceField(choices=DogSex.choices)
    breed = serializers.CharField()

    class Meta:
        model = Dog
        fields = [
            "ID",
            "shelterluvID",
            "name",
            "description",
            "photoURL",
            "ageMonths",
            "weight",
            "sex",
            "funSize",
            "breed",
            "availableNow",
            "availableDate",
            "interestCount",
        ]
