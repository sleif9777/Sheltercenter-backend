from rest_framework import serializers

from .models import AppointmentBase

class AppointmentBaseSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = AppointmentBase
        fields = ['id', 'weekday', 'time', 'type', 'instant']