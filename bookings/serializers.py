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
    sentLimitedPuppies = serializers.BooleanField(source="sent_limited_puppies")
    sentLimitedSmallPuppies = serializers.BooleanField(source="sent_limited_small_puppies")
    sentLimitedHypo = serializers.BooleanField(source="sent_limited_hypo")
    sentLimitedFunSize = serializers.BooleanField(source="sent_limited_fun_size")
    sentDogsWereAdopted = serializers.BooleanField(source="sent_dogs_were_adopted")
    sentDogsNotHereYet = serializers.BooleanField(source="sent_dogs_not_here_yet")
    sentXInQueue = serializers.BooleanField(source="sent_x_in_queue")

    class Meta:
        model = Booking
        fields = [
            'id', 
            'adopter', 
            'status', 
            'previousVisits', 
            'created', 
            'modified',
            'sentLimitedPuppies',
            'sentLimitedSmallPuppies',
            'sentLimitedHypo',
            'sentLimitedFunSize',
            'sentDogsWereAdopted',
            'sentDogsNotHereYet',
            'sentXInQueue'
        ]