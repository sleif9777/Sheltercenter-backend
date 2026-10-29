from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.request import Request

from adopters.models import Adopter
from adopters.views import AdopterViewSet

from .models import ChatbotInteraction
from .serializers import AskRequestSerializer, InteractionIDRequestSerializer
from .services import ChatbotService


class ChatbotViewSet(viewsets.GenericViewSet):
    queryset = ChatbotInteraction.objects.all()

    # GET commands
    @action(detail=False, methods=["GET"], url_path="GetStatus")
    def GetStatus(self, request: Request) -> JsonResponse:
        adopter = AdopterViewSet.UnpackAdopterFromAdopterIDRequest(request.query_params)

        if not AdopterViewSet._is_own_adopter_or_staff(request, adopter):
            return JsonResponse({}, status=status.HTTP_403_FORBIDDEN)

        return JsonResponse(
            {
                "enabled": adopter.chatbot_enabled,
                "questionsRemaining": ChatbotInteraction.questions_remaining_today(adopter),
            },
            status=status.HTTP_200_OK,
        )

    # POST commands
    @action(detail=False, methods=["POST"], url_path="Ask")
    def Ask(self, request: Request) -> JsonResponse:
        query = AskRequestSerializer(data=request.data)
        query.is_valid(raise_exception=True)

        adopter = Adopter.objects.get(pk=int(query.validated_data["adopterID"]))

        if not AdopterViewSet._is_own_adopter_or_staff(request, adopter):
            return JsonResponse({}, status=status.HTTP_403_FORBIDDEN)

        if not adopter.chatbot_enabled:
            return JsonResponse({}, status=status.HTTP_403_FORBIDDEN)

        if ChatbotInteraction.questions_remaining_today(adopter) == 0:
            return JsonResponse({"questionsRemaining": 0}, status=status.HTTP_429_TOO_MANY_REQUESTS)

        interaction = ChatbotService().ask(
            adopter, query.validated_data["question"].strip(), query.validated_data["message"]
        )
        offer = interaction.offered_appointment
        current = adopter.get_current_appointment()

        return JsonResponse(
            {
                "interactionID": interaction.id,
                # Shown to the adopter; may be set even when the message also went to staff
                "answer": interaction.answer,
                "sentToStaff": interaction.bot_escalated,
                # An open time the adopter can move their appointment to with one click
                "offer": {"label": ChatbotService.offer_label(offer)} if offer else None,
                # The adopter's current appointment, when the chatbot offered to cancel it
                "offerCancel": (
                    {"label": ChatbotService.offer_label(current)}
                    if interaction.offered_cancellation and current
                    else None
                ),
                "questionsRemaining": ChatbotInteraction.questions_remaining_today(adopter),
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=False, methods=["POST"], url_path="SendToStaff")
    def SendToStaff(self, request: Request) -> JsonResponse:
        query = InteractionIDRequestSerializer(data=request.data)
        query.is_valid(raise_exception=True)

        interaction = get_object_or_404(
            ChatbotInteraction, pk=query.validated_data["interactionID"]
        )

        if interaction.adopter is None or not AdopterViewSet._is_own_adopter_or_staff(
            request, interaction.adopter
        ):
            return JsonResponse({}, status=status.HTTP_403_FORBIDDEN)

        ChatbotService().send_to_staff(interaction)

        return JsonResponse({}, status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=["POST"], url_path="AcceptOffer")
    def AcceptOffer(self, request: Request) -> JsonResponse:
        query = InteractionIDRequestSerializer(data=request.data)
        query.is_valid(raise_exception=True)

        interaction = get_object_or_404(
            ChatbotInteraction, pk=query.validated_data["interactionID"]
        )
        adopter = interaction.adopter

        if adopter is None or not AdopterViewSet._is_own_adopter_or_staff(request, adopter):
            return JsonResponse({}, status=status.HTTP_403_FORBIDDEN)

        new_slot = ChatbotService.accept_offer(interaction)
        if new_slot is None:
            return JsonResponse(
                {"error": "Sorry, that time is no longer available."},
                status=status.HTTP_409_CONFLICT,
            )

        return JsonResponse(
            {
                "label": ChatbotService.offer_label(new_slot),
                "currentAppt": adopter.get_current_appointment_summary(),
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=False, methods=["POST"], url_path="AcceptCancellation")
    def AcceptCancellation(self, request: Request) -> JsonResponse:
        query = InteractionIDRequestSerializer(data=request.data)
        query.is_valid(raise_exception=True)

        interaction = get_object_or_404(
            ChatbotInteraction, pk=query.validated_data["interactionID"]
        )
        adopter = interaction.adopter

        if adopter is None or not AdopterViewSet._is_own_adopter_or_staff(request, adopter):
            return JsonResponse({}, status=status.HTTP_403_FORBIDDEN)

        canceled = ChatbotService.accept_cancellation(interaction)
        if canceled is None:
            return JsonResponse(
                {"error": "Sorry, that appointment can no longer be canceled here."},
                status=status.HTTP_409_CONFLICT,
            )

        return JsonResponse(
            {"label": ChatbotService.offer_label(canceled)}, status=status.HTTP_200_OK
        )
