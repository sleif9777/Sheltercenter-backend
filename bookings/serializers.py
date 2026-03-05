from adopters.serializers import *
from dogs.models import Dog
from dogs.serializers import WatchlistDogSerializer
from rest_framework import serializers

from .models import Booking


class BookingCardModelSerializer(serializers.ModelSerializer):
    ID = serializers.IntegerField(source="id")
    bookedInstant = serializers.CharField(source="created_display")
    flags = serializers.SerializerMethodField()

    class Meta:
        model = Booking
        fields = [
            "ID",
            "bookedInstant",
            "flags",
        ]

    def to_representation(self, instance: Booking):
        data = super().to_representation(instance)
        adopter = instance.adopter
        dogs = Dog.objects.filter(interest_adopters__pk=adopter.id)

        data["adopter"] = {
            "demographics": AdopterDemographicsSerializer(
                adopter,
                context=self.context,
            ).data,
            "preferences": AdopterPreferencesResponseSerializer(
                adopter,
                context=self.context,
            ).data,
            "watchlist": [WatchlistDogSerializer(dog).data for dog in dogs] if len(dogs) > 0 else []
        }

        return {k: v for k, v in data.items() if (v != "")}

    def get_flags(self, obj):
        return obj.sent_template_flags
