from rest_framework import serializers

from appointments.serializers import TimeRequestSerializer
from .models import AppointmentBase


class WeekdayRequestSerializer(serializers.Serializer):
    weekday = serializers.IntegerField(required=True, min_value=0, max_value=6)


class CreateTemplateAppointmentRequestSerializer(WeekdayRequestSerializer, TimeRequestSerializer):
    weekday = serializers.IntegerField(required=True, min_value=0, max_value=6)
    type = serializers.IntegerField(required=True)


class AppointmentBaseSerializer(serializers.HyperlinkedModelSerializer):
    timeDisplay = serializers.CharField(source="time_display")

    class Meta:
        model = AppointmentBase
        fields = ["id", "weekday", "time", "type", "instant", "timeDisplay"]
