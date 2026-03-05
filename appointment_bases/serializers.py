from rest_framework import serializers

from .models import AppointmentBase


class WeekdayRequestSerializer(serializers.Serializer):
    weekday = serializers.IntegerField(required=True, min_value=0, max_value=6)


class CreateTemplateAppointmentRequestSerializer(WeekdayRequestSerializer):
    hour = serializers.IntegerField(required=True, min_value=0, max_value=23)
    minute = serializers.IntegerField(required=True, min_value=0, max_value=59)
    weekday = serializers.IntegerField(required=True, min_value=0, max_value=6)
    type = serializers.IntegerField(required=True)


class AppointmentBaseSerializer(serializers.HyperlinkedModelSerializer):
    timeDisplay = serializers.CharField(source="time_display")

    class Meta:
        model = AppointmentBase
        fields = ["id", "weekday", "time", "type", "instant", "timeDisplay"]
