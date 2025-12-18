from rest_framework import serializers

from bookings.serializers import BookingSerializer

from .models import Appointment

class AppointmentSerializer(serializers.HyperlinkedModelSerializer):
    id = serializers.IntegerField()
    type = serializers.IntegerField()
    instant = serializers.DateTimeField()
    locked = serializers.BooleanField()
    bookings = BookingSerializer(many=True, read_only=True)
    checkInTime = serializers.DateTimeField(source="check_in_time")
    checkOutTime = serializers.DateTimeField(source="check_out_time")
    clothingDescription = serializers.CharField(source="clothing_description")
    counselor = serializers.CharField()
    outcome = serializers.IntegerField()
    chosenDog = serializers.CharField(source="chosen_dog")
    sourceAdoptionDog = serializers.SlugRelatedField(
        source="source_adoption",
        many=False,
        read_only=True,
        slug_field="dog"
    )
    sourceAdoptionID = serializers.PrimaryKeyRelatedField(
        source="source_adoption",
        many=False,
        read_only=True
    )
    paperworkAdoptionDog = serializers.SlugRelatedField(
        source="paperwork_adoption",
        many=False,
        read_only=True,
        slug_field="dog"
    )
    paperworkAdoptionID = serializers.PrimaryKeyRelatedField(
        source="paperwork_adoption",
        many=False,
        read_only=True,
    )
    heartwormPositive = serializers.BooleanField(source="paperwork_adoption.heartworm_positive")
    appointmentNotes = serializers.CharField(source="appointment_notes")
    surrenderedDog = serializers.CharField(source="surrendered_dog")
    surrenderedDogFka = serializers.CharField(source="surrendered_dog_fka")

    class Meta:
        model = Appointment
        fields = [
            'id',
            'type',
            'instant',
            'locked',
            'bookings',
            'checkInTime',
            'checkOutTime',
            'clothingDescription',
            'counselor',
            'outcome',
            'chosenDog',
            'sourceAdoptionDog',
            'sourceAdoptionID',
            'paperworkAdoptionDog',
            'paperworkAdoptionID',
            'heartwormPositive',
            'appointmentNotes',
            'surrenderedDog',
            'surrenderedDogFka',
        ]