from adopters.serializers import AdopterDemographicsSerializer
from dogs.models import Dog
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
    dog = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    dogID = serializers.CharField(required=True)
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


class DashboardPendingAdoptionDogSerializer(serializers.Serializer):
    ID = serializers.IntegerField(source="dogID")
    name = serializers.CharField(source="dog")
    photoURL = serializers.SerializerMethodField()
    unavailableDate = serializers.SerializerMethodField()

    def _get_dog(self, obj):
        if not hasattr(obj, "_cached_dog"):
            if not obj.dogID:
                obj._cached_dog = None
            else:
                try:
                    obj._cached_dog = Dog.objects.get(pk=obj.dogID)
                except Dog.DoesNotExist:
                    obj._cached_dog = None
        return obj._cached_dog

    def get_photoURL(self, obj):
        dog = self._get_dog(obj)
        return dog.photo_url if dog else "https://new-s3.shelterluv.com/public/img/profile_photo/default_dog.png"

    def get_unavailableDate(self, obj):
        dog = self._get_dog(obj)
        if dog:
            return dog.unavailable_date_iso
        return obj.source_appt_instant if obj.source_appointment else None


class PendingAdoptionValueLabelPairSerializer(serializers.HyperlinkedModelSerializer):
    ID = serializers.IntegerField(source="id")
    description = serializers.CharField()

    class Meta:
        model = PendingAdoption
        fields = [
            "ID",
            "description",
        ]


class PendingAdoptionsSerializer(PendingAdoptionValueLabelPairSerializer):
    sourceAppointmentInst = serializers.CharField(source="source_appt_instant", read_only=True)
    paperworkAppointmentInst = serializers.CharField(
        source="paperwork_appt_instant", read_only=True
    )
    created = serializers.DateTimeField(source="created_instant")
    circumstance = serializers.IntegerField()
    dog = serializers.CharField()
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
