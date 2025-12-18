from rest_framework import serializers

from .models import PendingAdoptionUpdate

class PendingAdoptionUpdatesSerializer(serializers.HyperlinkedModelSerializer):
    id = serializers.IntegerField()
    instant = serializers.DateTimeField()

    class Meta:
        model = PendingAdoptionUpdate
        fields = [
            'id',
            'instant'
        ]