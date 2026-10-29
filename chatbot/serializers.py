from rest_framework import serializers

from adopters.serializers import AdopterIDRequestSerializer

from .models import ChatbotInteraction


class AskRequestSerializer(AdopterIDRequestSerializer):
    question = serializers.CharField(max_length=ChatbotInteraction.MAX_QUESTION_LENGTH)


class InteractionIDRequestSerializer(serializers.Serializer):
    interactionID = serializers.IntegerField()
