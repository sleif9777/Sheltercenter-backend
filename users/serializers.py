from adopters import serializers
from adopters.enums import ApprovalStatus
from .enums import FormContexts, SecurityLevel
from .models import UserProfile

from rest_framework import serializers

# REQUESTS

class ImportSpreadsheetBatchRequestSerializer(serializers.Serializer):
    importFile = serializers.FileField()

    def validate_importFile(self, file):
        if not file.name.lower().endswith((".xlsx", ".csv")):
            raise serializers.ValidationError("Unsupported file type.")
        return file


class PrimaryEmailRequestSerializer(serializers.Serializer):
    primaryEmail = serializers.CharField(required=True)

    def validate_primaryEmail(self, value: str) -> str:
        user_profiles = UserProfile.objects.filter(primary_email=value)
        if not user_profiles.exists():
            raise serializers.ValidationError("User does not exist.")
        if user_profiles.count() > 1:
            raise serializers.ValidationError("Multiple users found with the same email.")
        return value

    def get_user(self) -> UserProfile:
        email: str = self.validated_data["primaryEmail"]
        return UserProfile.objects.get(primary_email=email)


class UpdatePrimaryEmailRequestSerializer(PrimaryEmailRequestSerializer):
    newEmail = serializers.EmailField()


class SaveUserFormRequestSerializer(serializers.Serializer):
    context = serializers.ChoiceField(
        choices=FormContexts.choices, required=False, default=FormContexts.NEW
    )

    status = serializers.ChoiceField(choices=ApprovalStatus.choices)

    primaryEmail = serializers.EmailField()

    firstName = serializers.CharField()
    lastName = serializers.CharField()

    internalNotes = serializers.CharField(required=False, allow_blank=True, default="")

# RESPONSES

class LogInUserSerializer(serializers.Serializer):
    ID = serializers.IntegerField()
    adopterID = serializers.IntegerField(required=False, allow_null=True)
    firstName = serializers.CharField()
    lastName = serializers.CharField()
    securityLevel = serializers.ChoiceField(choices=SecurityLevel.choices)


class LogInResponseSerializer(serializers.Serializer):
    isAuthenticated = serializers.BooleanField()
    user = LogInUserSerializer()
    accessToken = serializers.CharField()
    refreshToken = serializers.CharField()

    