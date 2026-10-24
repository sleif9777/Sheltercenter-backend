import logging

from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpRequest, JsonResponse
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken

logger = logging.getLogger(__name__)

from users.enums import SecurityLevel
from users.factories import UserFormFactory, UserSpreadsheetFactory
from users.permissions import MinSecurityLevel

from .models import UserProfile
from .serializers import *


# Create your views here.
class UserProfileViewSet(viewsets.ModelViewSet):
    queryset = UserProfile.objects.all()

    # GET methods
    @action(detail=False, methods=["GET"], url_path="LogIn", permission_classes=[AllowAny])
    def LogIn(self, request: HttpRequest):
        try:
            query = PrimaryEmailRequestSerializer(data=request.query_params)
            query.is_valid(raise_exception=True)
            user = query.get_user()

            access_token = AccessToken.for_user(user)
            refresh_token = RefreshToken.for_user(user)
            if user.adopter_profile is not None and user.adopter_profile.approval_expired:
                return JsonResponse(
                    {},
                    status=status.HTTP_418_IM_A_TEAPOT
                )
            
            return JsonResponse(
                {
                    "isAuthenticated": True,
                    "user": {
                        "userID": user.id,
                        "firstName": user.first_name,
                        "lastName": user.last_name,
                        "adopterID": user.adopter_profile.id if user.adopter_profile else None,
                        "security": user.security_level,
                        "currentAppt": (
                            user.adopter_profile.get_current_appointment_summary()
                            if user.adopter_profile
                            else None
                        ),
                        "restrictCalendar": user.adoption_completed,
                    },
                    "refreshToken": str(refresh_token),
                    "accessToken": str(access_token),
                },
                status=status.HTTP_202_ACCEPTED,
            )
        except ObjectDoesNotExist:
            return JsonResponse({"isAuthenticated": False}, status=status.HTTP_401_UNAUTHORIZED)
        except Exception:
            logger.exception("Unexpected error during LogIn")
            return JsonResponse({"isAuthenticated": False}, status=status.HTTP_401_UNAUTHORIZED)

    # POST methods
    @action(detail=False, methods=["POST"], url_path="ImportSpreadsheetBatch", permission_classes=[MinSecurityLevel(SecurityLevel.ADMIN)])
    def ImportSpreadsheetBatch(self, request):
        query = ImportSpreadsheetBatchRequestSerializer(data=request.data)
        query.is_valid(raise_exception=True)

        import_file = query.validated_data["importFile"]
        skip_approval_emails: bool = query.validated_data["skipApprovalEmails"]

        upload_result = UserSpreadsheetFactory(
            import_file, send_approval_emails=not skip_approval_emails
        ).run_import_batch()

        return JsonResponse(upload_result, status=status.HTTP_200_OK)

    @action(detail=False, methods=["POST"], url_path="SaveUserForm", permission_classes=[MinSecurityLevel(SecurityLevel.ADMIN)])
    def SaveUserForm(self, request):
        query = SaveUserFormRequestSerializer(data=request.data)
        query.is_valid(raise_exception=True)

        _, created, averted = UserFormFactory(query.validated_data).process_form_data()

        if created:
            respStatus = status.HTTP_201_CREATED
        elif averted:
            respStatus = status.HTTP_203_NON_AUTHORITATIVE_INFORMATION
        else:
            respStatus = status.HTTP_202_ACCEPTED

        return JsonResponse({}, status=respStatus)

    @action(detail=False, methods=["POST"], url_path="UpdatePrimaryEmail")
    def UpdatePrimaryEmail(self, request):
        query = UpdatePrimaryEmailRequestSerializer(data=request.data)
        query.is_valid(raise_exception=True)

        new_email = query.validated_data.get("newEmail")

        try:
            UserProfile.objects.get(primary_email=new_email)
            return JsonResponse({}, status=status.HTTP_226_IM_USED)
        except ObjectDoesNotExist: # Good error! No match = update as expected
            user = query.get_user()
            user.update_email(new_email)

            return JsonResponse({}, status=status.HTTP_200_OK)
