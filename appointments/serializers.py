from datetime import date

from adopters.serializers import AdopterPreferencesRequestSerializer
from bookings.serializers import BookingCardModelSerializer
from rest_framework import serializers

from .enums import OutcomeTypes
from .models import Appointment

# REQUESTS


class AppointmentIDRequestSerializer(serializers.Serializer):
    apptID = serializers.IntegerField()

    def validate_apptID(self, value: str) -> int:
        if not Appointment.objects.filter(pk=int(value)).exists():
            raise serializers.ValidationError("Appointment does not exist.")
        return value


class CheckInAppointmentRequestSerializer(AppointmentIDRequestSerializer):
    clothingDescription = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
    )
    counselor = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
    )
    streetAddress = serializers.CharField()
    city = serializers.CharField()
    state = serializers.CharField()
    postalCode = serializers.CharField()
    

class CheckOutAppointmentRequestSerializer(AppointmentIDRequestSerializer):
    outcome = serializers.IntegerField()
    sendSleepoverInfo = serializers.BooleanField()
    dogID = serializers.CharField(required=False, allow_null=True, allow_blank=True)

    def validate(self, data):
        outcome = data["outcome"]
        dogID = data.get("dogID")

        if outcome < OutcomeTypes.NO_DECISION and not dogID:
            raise serializers.ValidationError({"dog": "This field is required."})

        return data


class CreateWalkInRequestSerializer(serializers.Serializer):
    adopterID = serializers.CharField()
    firstName = serializers.CharField(
        max_length=255,
        required=False,
        allow_blank=True,
    )
    lastName = serializers.CharField(
        max_length=255,
        required=False,
        allow_blank=True,
    )
    primaryEmail = serializers.EmailField(
        required=False,
        allow_blank=True,
    )
    type = serializers.IntegerField(required=True)

    def validate_adopterID(self, value):
        if value == "*":
            return value

        try:
            int_value = int(value)
        except (TypeError, ValueError):
            raise serializers.ValidationError(
                "adopterID must be an integer or '*'"
            )

        if int_value < 0:
            raise serializers.ValidationError(
                "adopterID must be a positive integer"
            )

        return int_value

    def validate(self, attrs):
        adopter_id = attrs.get("adopterID")

        # If wildcard, require full adopter info
        if adopter_id == "*":
            missing = [
                field for field in ("firstName", "lastName", "primaryEmail")
                if not attrs.get(field)
            ]

            if missing:
                raise serializers.ValidationError({
                    field: "This field is required when adopterID is '*'."
                    for field in missing
                })

        return attrs
    

class ISODateRequestSerializer(serializers.Serializer):
    isoDate = serializers.CharField()

    def validate_isoDate(self, isoDate: str) -> date:
        try:
            year, month, day = map(int, isoDate.split("-"))
            isoDate = date(year, month, day)
        except (ValueError, TypeError):
            raise serializers.ValidationError("Not a valid ISO date (YYYY-MM-DD).")

        return isoDate


class CreateAppointmentRequestSerializer(ISODateRequestSerializer):
    hour = serializers.IntegerField(required=True, min_value=0, max_value=23)
    minute = serializers.IntegerField(required=True, min_value=0, max_value=59)
    fka = serializers.CharField(required=False, allow_null=True)
    type = serializers.IntegerField(required=True)
    locked = serializers.BooleanField()
    notes = serializers.CharField(required=False, allow_null=True)
    pendingAdoptionID = serializers.IntegerField(required=False)


class ScheduleAppointmentRequestSerializer(AppointmentIDRequestSerializer, AdopterPreferencesRequestSerializer):
    pass

# RESPONSES

class AppointmentCardDataSerializer(serializers.ModelSerializer):
    ID = serializers.IntegerField(source="id")

    type = serializers.IntegerField()
    typeDisplay = serializers.CharField(source="type_display")

    description = serializers.CharField()
    weekday = serializers.IntegerField()
    instantDisplay = serializers.CharField(source="instant_display")

    locked = serializers.BooleanField()
    softDeleted = serializers.BooleanField(source="soft_deleted")
    hasCurrentBooking = serializers.BooleanField(source="has_current_booking")

    outcomeDisplay = serializers.CharField(source="outcome_value_display")
    outcome = serializers.IntegerField(read_only=True, allow_null=True)
    chosenDog = serializers.CharField(source="chosen_dog", allow_null=True)

    checkInTime = serializers.CharField(read_only=True, allow_null=True)
    clothingDescription = serializers.CharField(read_only=True, allow_null=True)
    counselor = serializers.CharField(read_only=True, allow_null=True)

    checkOutTime = serializers.CharField(read_only=True, allow_null=True)

    class Meta:
        model = Appointment
        fields = [
            "ID",
            "type",
            "typeDisplay",
            "description",
            "weekday",
            "instantDisplay",
            "locked",
            "softDeleted",
            "hasCurrentBooking",
            "checkInTime",
            "clothingDescription",
            "counselor",
            "checkOutTime",
            "outcomeDisplay",
            "outcome",
            "chosenDog"
        ]

    def to_representation(self, instance: Appointment):
        data = super().to_representation(instance)
        booking = instance.get_current_booking()

        if instance.is_adoption_appointment and booking is not None:
            data["booking"] = BookingCardModelSerializer(
                booking,
                context=self.context,
            ).data
            data["outcome"] = instance.outcome or None

            if instance.is_checked_in:
                data["checkInTime"] = instance.check_in_time_display
                data["clothingDescription"] = instance.clothing_description
                data["counselor"] = instance.counselor

            if instance.is_checked_out:
                data["checkOutTime"] = instance.check_out_time_display
                data["outcomeDisplay"] = instance.outcome_value_display

        return {k: v for k, v in data.items() if (v != "")}


class AppointmentMissingOutcomeSerializer(serializers.Serializer):
    ID = serializers.IntegerField(source="id")
    description = serializers.CharField()
    isoDate = serializers.CharField(source="iso_date")

    class Meta:
        model = Appointment
        fields = [
            "ID",
            "description",
            "isoDate",
        ]


class ReportingAdminAppointmentSerializer(serializers.ModelSerializer): 
    ID = serializers.IntegerField(source="id")
    timeDisplay = serializers.CharField(source="time_display")
    description = serializers.CharField()
    type = serializers.IntegerField()
    typeDisplay = serializers.CharField(source="type_display")
    notes = serializers.CharField(source="appointment_notes")

    class Meta:
        model = Appointment
        fields = [
            "ID",
            "timeDisplay",
            "description",
            "type",
            "typeDisplay",
            "notes",
        ]
        

class ReportingAdoptionAppointmentSerializer(serializers.ModelSerializer):
    ID = serializers.IntegerField(source="id")
    timeDisplay = serializers.CharField(source="time_display")
    description = serializers.CharField()
    checkInTime = serializers.CharField(source="check_in_time_display")
    checkOutTime = serializers.CharField(source="check_out_time_display")
    counselor = serializers.CharField()
    clothingDescription = serializers.CharField(source="clothing_description")
    type = serializers.IntegerField()
    typeDisplay = serializers.CharField(source="type_display")
    outcomeDisplay = serializers.CharField(source="outcome_value_display")
    chosenDog = serializers.CharField(source="chosen_dog")

    class Meta:
        model = Appointment
        fields = [
            "ID",
            "timeDisplay",
            "description",
            "checkInTime",
            "checkOutTime",
            "counselor",
            "clothingDescription",
            "type",
            "typeDisplay",
            "outcomeDisplay",
            "chosenDog",
        ]

    def to_representation(self, instance: Appointment):
        data = super().to_representation(instance)
        booking = instance.get_current_booking()

        if instance.is_adoption_appointment and booking is not None:
            data["booking"] = BookingCardModelSerializer(
                booking,
            ).data

        return {k: v for k, v in data.items() if (v != "")}
