import mimetypes
import traceback

from django.contrib.auth import login
from django.core.exceptions import ObjectDoesNotExist
from django.http import JsonResponse
from http import HTTPStatus
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework_simplejwt.tokens import RefreshToken, AccessToken, BlacklistedToken

from adopters.serializers import AdopterSerializer

from .models import UserProfile

# Create your views here.
class UserProfileViewSet(viewsets.ModelViewSet):
    queryset = UserProfile.objects.all()
    serializer_class = AdopterSerializer

    @action(detail=False, methods=["POST"], url_path="GenerateOTP")
    def GenerateOTP(self, request, *args, **kwargs):
        try:
            # Confirm a user exists
            try:
                user = UserProfile.objects.get(primary_email=request.data["email"])
            except ObjectDoesNotExist:
                return JsonResponse({
                    "message": "No user exists with this email address. Email adoptions@savinggracenc.org for assistance."
                }, status=status.HTTP_200_OK)
            
            # If still timed out, quit early
            if user.timed_out:
                return JsonResponse({
                    "message": "Max attempts reached. Try again in 15 minutes."
                }, status=status.HTTP_200_OK)
            
            user.reset_otp()

            return JsonResponse({
                "message": "New one-time password sent to your email."
            }, status=status.HTTP_202_ACCEPTED)
        except Exception as e:
            print(e)
            return JsonResponse({
                "message": "Something went wrong. Contact an administrator for help."
            }, status=status.HTTP_200_OK)
        
    @action(detail=False, methods=["POST"], url_path="AuthenticateOTP")
    def AuthenticateOTP(self, request, *args, **kwargs):
        ## CONFIRM A USER EXISTS
        # Find the user
        try:
            user = UserProfile.objects.get(primary_email=request.data["email"])
            password = request.data["otp"]
        # If no user
        except ObjectDoesNotExist:
            return JsonResponse({
                "isAuthenticated": False,
                "message": "No user exists with this email address. Email adoptions@savinggracenc.org for assistance."
            }, status=status.HTTP_200_OK)
        # Blank OTP
        except KeyError:
            return JsonResponse({
                "isAuthenticated": False,
                "message": "Password entry invalid."
            }, status=status.HTTP_200_OK)
        
        ## VALIDATE SAVED OTP IS STILL VALID AND ACTIVE
        # If user is timed out, quit early
        if user.timed_out:
            return JsonResponse({
                "isAuthenticated": False,
                "message": "Max attempts reached. Try again in 15 minutes."
            }, status=status.HTTP_200_OK)
        # If OTP expired, prompt user to refresh and regenerate
        if user.otp_expired:
            return JsonResponse({
                "isAuthenticated": False,
                "message": "Password is expired. Refresh the page and try again."
            }, status=status.HTTP_200_OK)
        
        ## ATTEMPT LOGIN
        if password == user.otp:
            login(request, user)

            access_token = AccessToken.for_user(user)
            refresh_token = RefreshToken.for_user(user)

            return JsonResponse(
                {
                    "isAuthenticated": True,
                    "userID": user.id,
                    "securityLevel": user.security_level,
                    'refreshToken': str(refresh_token),
                    'accessToken': str(access_token),
                },
                status=status.HTTP_202_ACCEPTED
            )
        # Failed
        else:
            maxed_out = user.failed_authentication()

            if maxed_out:
                message = "Max attempts reached. Try again in 15 minutes."
            else:
                message = "Incorrect password. Try again."

            return JsonResponse({
                "isAuthenticated": False,
                "message": message
            }, status=status.HTTP_200_OK)

    @action(detail=False, methods=["POST"], url_path="SaveAdopterByForm")
    def SaveAdopterByForm(self, request, *args, **kwargs):
        adopter, created, averted = UserProfile.create_update_by_form(request.data)

        if created:
            respStatus = status.HTTP_201_CREATED
        elif averted:
            respStatus = status.HTTP_203_NON_AUTHORITATIVE_INFORMATION
        else:
            respStatus = status.HTTP_202_ACCEPTED

        return JsonResponse(
            { 
                "adopter": AdopterSerializer(adopter).data, 
            },
            status=respStatus
        )
    
    @action(detail=False, methods=["POST"], url_path="UpdatePrimaryEmail")
    def UpdatePrimaryEmail(self, request, *args, **kwargs):
        email_key = request.data["emailKey"]
        new_email = request.data["newEmail"]

        user = UserProfile.objects.get(primary_email=email_key)
        user.update_email(new_email)

        return JsonResponse(
            { 
                "adopter": AdopterSerializer(user.adopter_profile).data, 
            }
        )
    
    @action(detail=False, methods=["POST"], url_path="SpreadsheetImportBatch")
    def SpreadsheetImportBatch(self, request, *args, **kwargs):
        try:
            print(request.data, request.FILES)
            if "batchFile" not in request.FILES:
                print("not in request".upper())
                return JsonResponse({ status: HTTPStatus.BAD_REQUEST })
            
            importFile = request.FILES.values()
            fileType, _ = mimetypes.guess_type(importFile.temporary_file_path())
            print(request.FILES["batchFile"], type(request.FILES["batchFile"]), importFile.temporary_file_path(), fileType, type(request.FILES.get("batchFile")))

            if fileType is None:
                match importFile.temporary_file_path.split(".")[1]:
                    case "csv":
                        print("AAA")
                        fileType = "text/csv"
                    case "xlsx":
                        print("BBB")
                        fileType == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

            if fileType == "text/csv":
                successes, updates, failures, aversions = UserProfile.import_csv_spreadsheet_batch(importFile)
                return JsonResponse(
                    {
                        "successes": successes,
                        "updates": updates,
                        "failures": failures,
                        "aversions": [AdopterSerializer(adopter).data for adopter in aversions],
                    },
                    status=status.HTTP_201_CREATED,
                )
            elif fileType == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet":
                successes, updates, failures, aversions = UserProfile.import_xlsx_spreadsheet_batch(importFile)
                return JsonResponse(
                    {
                        "successes": successes,
                        "updates": updates,
                        "failures": failures,
                        "aversions": [AdopterSerializer(adopter).data for adopter in aversions],
                    },
                    status=status.HTTP_201_CREATED,
                )
            else:
                print("NOPE")
                return JsonResponse({}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            print("EXCEPT", e)
            traceback.print_exc()
            return JsonResponse({}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=["POST"], url_path="GetCurrentAuth")
    def GetCurrentAuth(self, request, *args, **kwargs):
        if "userID" in request.data:
            try:
                user = UserProfile.objects.get(pk=request.data["userID"])

                return JsonResponse(
                    {
                        "isAuthenticated": True,
                        "userID": user.id,
                        "securityLevel": user.security_level
                    }
                )
            except ObjectDoesNotExist:
                pass

        return JsonResponse(
            {
                "isAuthenticated": False
            }
        )