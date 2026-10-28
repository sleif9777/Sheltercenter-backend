from datetime import date
from typing import Any

from django.utils import timezone
from rest_framework import serializers

from dogs.models import Dog

from .models import DashboardNote

DEFAULT_DOG_PHOTO = "https://new-s3.shelterluv.com/public/img/profile_photo/default_dog.png"


# REQUESTS
class CreateDashboardNoteRequestSerializer(serializers.Serializer):
    dogID = serializers.IntegerField(required=False, allow_null=True)
    dogName = serializers.CharField(required=False, allow_blank=True, max_length=100)
    note = serializers.CharField(max_length=200)
    showUntil = serializers.DateField(required=False, allow_null=True)

    def validate_showUntil(self, value: date | None) -> date | None:
        if value is not None and value < timezone.localdate():
            raise serializers.ValidationError("Must be today or later.")
        return value

    def validate_dogID(self, value: int | None) -> int | None:
        if value is not None and not Dog.objects.filter(pk=value).exists():
            raise serializers.ValidationError("Dog does not exist.")
        return value

    def validate(self, data: dict[str, Any]) -> dict[str, Any]:
        has_dog = data.get("dogID") is not None
        has_name = bool(data.get("dogName", "").strip())

        if has_dog == has_name:
            raise serializers.ValidationError("Choose a dog or enter its name, but not both.")
        return data


class DashboardNoteIDRequestSerializer(serializers.Serializer):
    noteID = serializers.IntegerField()


# RESPONSES
class DashboardNoteSerializer(serializers.ModelSerializer):
    ID = serializers.IntegerField(source="id")
    dogID = serializers.IntegerField(source="dog_id", allow_null=True)
    dogName = serializers.CharField(source="display_name")
    note = serializers.CharField()
    photoURL = serializers.SerializerMethodField()
    showUntil = serializers.DateField(source="show_until", allow_null=True)

    class Meta:
        model = DashboardNote
        fields = ["ID", "dogID", "dogName", "note", "photoURL", "showUntil"]

    def get_photoURL(self, obj: DashboardNote) -> str:
        return obj.dog.photo_url if obj.dog and obj.dog.photo_url else DEFAULT_DOG_PHOTO
