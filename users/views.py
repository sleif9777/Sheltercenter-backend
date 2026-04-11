from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpRequest, JsonResponse
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken

from auth.security import IsAdminUser

from appointments.models import Appointment
from users.factories import UserFormFactory, UserSpreadsheetFactory

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
            current_appt: Appointment | None = None

            if user.adopter_profile:
                current_appt = user.adopter_profile.get_current_appointment()

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
                            {
                                "ID": current_appt.id,
                                "isoDate": timezone.localtime(current_appt.instant).date().isoformat(),
                                "instantDisplay": current_appt.instant_display,
                            }
                            if current_appt
                            else None
                        ),
                        "restrictCalendar": user.adoption_completed,
                    },
                    "refreshToken": str(refresh_token),
                    "accessToken": str(access_token),
                },
                status=status.HTTP_202_ACCEPTED,
            )
        except:
            return JsonResponse(
                {
                    "isAuthenticated": False,
                },
                status=status.HTTP_401_UNAUTHORIZED,
            )

    # POST methods
    @action(detail=False, methods=["POST"], url_path="ImportSpreadsheetBatch", permission_classes=[IsAdminUser])
    def ImportSpreadsheetBatch(self, request):
        query = ImportSpreadsheetBatchRequestSerializer(data=request.data)
        query.is_valid(raise_exception=True)

        import_file = query.validated_data["importFile"]

        upload_result = UserSpreadsheetFactory(import_file).run_import_batch()

        return JsonResponse(upload_result, status=status.HTTP_200_OK)

    @action(detail=False, methods=["POST"], url_path="SaveUserForm", permission_classes=[IsAuthenticated])
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

    @action(detail=False, methods=["POST"], url_path="UpdatePrimaryEmail", permission_classes=[IsAuthenticated])
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
