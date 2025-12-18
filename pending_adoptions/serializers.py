from rest_framework import serializers

from adopters.serializers import AdopterSerializer
from appointments.serializers import AppointmentSerializer
from pending_adoption_updates.serializers import PendingAdoptionUpdatesSerializer

from .models import PendingAdoption

class PendingAdoptionsSerializer(serializers.HyperlinkedModelSerializer):
    id = serializers.IntegerField()
    sourceAppointment = AppointmentSerializer(
        source="source_appointment", 
        read_only=True
    )
    paperworkAppointment = AppointmentSerializer(
        source="paperwork_appointment", 
        read_only=True
    )
    created = serializers.DateTimeField(source="created_instant")
    circumstance = serializers.IntegerField()
    dog = serializers.CharField()
    adopter = AdopterSerializer()
    readyToRollInstant = serializers.DateTimeField(source="ready_to_roll_instant")
    status = serializers.IntegerField()
    heartwormPositive = serializers.BooleanField(source="heartworm_positive")
    updates = PendingAdoptionUpdatesSerializer(many=True, read_only=True)

    class Meta:
        model = PendingAdoption
        fields = [
            'id',
            'sourceAppointment',
            'paperworkAppointment',
            'created',
            'circumstance',
            'dog',
            'adopter',
            'readyToRollInstant',
            'status',
            'heartwormPositive',
            'updates'
        ]