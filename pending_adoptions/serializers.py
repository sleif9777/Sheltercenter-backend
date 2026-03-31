from adopters.serializers import AdopterDemographicsSerializer
from pending_adoption_updates.serializers import PendingAdoptionUpdatesSerializer
from rest_framework import serializers

from .models import PendingAdoption


# REQUESTS
class AdoptionIDRequestSerializer(serializers.Serializer):
    adoptionID = serializers.IntegerField(required=True)

    def validate_adopterID(self, value: str) -> int:
        if not PendingAdoption.objects.filter(pk=int(value)).exists():
            raise serializers.ValidationError("Adoption does not exist.")
        return value

    def get_adoption(self) -> PendingAdoption:
        adoption_id: int = self.validated_data["adoptionID"]
        return PendingAdoption.objects.get(pk=adoption_id)


class ChangeDogRequestSerializer(AdoptionIDRequestSerializer):
    newDog = serializers.CharField(required=True)


class CreatePendingAdoptionRequestSerializer(serializers.Serializer):
    adopterID = serializers.IntegerField(required=True)
    dog = serializers.CharField(required=True)
    circumstance = serializers.IntegerField(required=True)


class CreatePendingAdoptionUpdateRequestSerializer:
    adoptionID = serializers.IntegerField(required=True)
    message = serializers.CharField(required=True)
    subject = serializers.CharField(required=True)


class MarkStatusRequestSerializer(AdoptionIDRequestSerializer):
    status = serializers.IntegerField(required=True)
    message = serializers.CharField(required=False, allow_blank=True)

class MarkHeartwormRequestSerializer(AdoptionIDRequestSerializer):
    heartworm = serializers.BooleanField(required=False, default=False)


# RESPONSES


class PendingAdoptionValueLabelPairSerializer(serializers.HyperlinkedModelSerializer):
    ID = serializers.IntegerField(source="id")
    description = serializers.CharField()

    class Meta:
        model = PendingAdoption
        fields = [
            "ID",
            "description",
        ]


class PendingAdoptionsSerializer(serializers.HyperlinkedModelSerializer):
    ID = serializers.IntegerField(source="id")
    sourceAppointmentInst = serializers.CharField(source="source_appt_instant", read_only=True)
    paperworkAppointmentInst = serializers.CharField(source="paperwork_appt_instant", read_only=True)
    created = serializers.DateTimeField(source="created_instant")
    circumstance = serializers.IntegerField()
    dog = serializers.CharField()
    description = serializers.CharField()
    adopter = AdopterDemographicsSerializer()
    readyToRollInstant = serializers.DateTimeField(source="ready_to_roll_instant")
    status = serializers.IntegerField()
    heartwormPositive = serializers.BooleanField(source="heartworm_positive")
    updates = PendingAdoptionUpdatesSerializer(many=True, read_only=True)

    class Meta:
        model = PendingAdoption
        fields = [
            "ID",
            "sourceAppointmentInst",
            "paperworkAppointmentInst",
            "created",
            "circumstance",
            "dog",
            "description",
            "adopter",
            "readyToRollInstant",
            "status",
            "heartwormPositive",
            "updates",
        ]
