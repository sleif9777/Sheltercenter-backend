from rest_framework import serializers

from .models import ClosedDate

class ClosedDateSerializer(serializers.HyperlinkedModelSerializer):
    id = serializers.IntegerField()
    date = serializers.DateField()

    class Meta:
        model = ClosedDate
        fields = ['id', 'date']