from rest_framework import serializers

from .models import PendingAdoptionUpdate


class PendingAdoptionUpdatesSerializer(serializers.HyperlinkedModelSerializer):
    instant = serializers.CharField()

    class Meta:
        model = PendingAdoptionUpdate
        fields = [
            'instant'
        ]