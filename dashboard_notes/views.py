from django.http import JsonResponse
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.request import Request

from users.enums import SecurityLevel
from users.permissions import AnySecurityLevel

from .models import DashboardNote
from .serializers import (
    CreateDashboardNoteRequestSerializer,
    DashboardNoteIDRequestSerializer,
    DashboardNoteSerializer,
)

# AnySecurityLevel, not MinSecurityLevel, so the dashboard login (a higher number) is not let in.
CAN_EDIT_NOTES = AnySecurityLevel(SecurityLevel.ADMIN, SecurityLevel.SUPERUSER)


# Notes are read with the rest of the dashboard in Dogs/GetDashboardDogHash.
class DashboardNoteViewSet(viewsets.GenericViewSet):
    queryset = DashboardNote.objects.all()

    # POST commands
    @action(
        detail=False,
        methods=["POST"],
        url_path="CreateDashboardNote",
        permission_classes=[CAN_EDIT_NOTES],
    )
    def CreateDashboardNote(self, request: Request) -> JsonResponse:
        query = CreateDashboardNoteRequestSerializer(data=request.data)
        query.is_valid(raise_exception=True)

        dog_id = query.validated_data.get("dogID")
        note = DashboardNote.objects.create(
            dog_id=dog_id,
            dog_name="" if dog_id is not None else query.validated_data["dogName"].strip(),
            note=query.validated_data["note"].strip(),
            show_until=query.validated_data.get("showUntil"),
        )

        return JsonResponse(
            {"note": DashboardNoteSerializer(note).data}, status=status.HTTP_201_CREATED
        )

    @action(
        detail=False,
        methods=["POST"],
        url_path="DeleteDashboardNote",
        permission_classes=[CAN_EDIT_NOTES],
    )
    def DeleteDashboardNote(self, request: Request) -> JsonResponse:
        query = DashboardNoteIDRequestSerializer(data=request.data)
        query.is_valid(raise_exception=True)

        # Already-deleted notes are fine: another superuser may have removed it first
        DashboardNote.objects.filter(pk=query.validated_data["noteID"]).delete()

        return JsonResponse({}, status=status.HTTP_200_OK)
