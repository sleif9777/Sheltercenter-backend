from rest_framework import serializers

from adopters.serializers import AdopterIDRequestSerializer

from .models import ChatbotInteraction


class AskRequestSerializer(AdopterIDRequestSerializer):
    question = serializers.CharField(max_length=ChatbotInteraction.MAX_QUESTION_LENGTH)
    # The message as written in the editor, formatting included, for the email to staff
    message = serializers.CharField(required=False, allow_blank=True, default="")


class InteractionIDRequestSerializer(serializers.Serializer):
    interactionID = serializers.IntegerField()
