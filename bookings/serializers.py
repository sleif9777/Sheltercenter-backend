from rest_framework import serializers

from adopters.serializers import AdopterSerializer
from .models import Booking

class BookingSerializer(serializers.HyperlinkedModelSerializer):
    id = serializers.IntegerField()
    adopter = AdopterSerializer(read_only=True)
    status = serializers.IntegerField()
    previousVisits = serializers.IntegerField(source="previous_visits")
    created = serializers.DateTimeField()
    modified = serializers.DateTimeField()

    class Meta:
        model = Booking
        fields = ['id', 'adopter', 'status', 'previousVisits', 'created', 'modified']