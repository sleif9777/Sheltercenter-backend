import datetime
import json
from .models import Adopter, AdopterStatuses
from .serializers import AdopterSerializer
from bookings.models import Booking, BookingStatus

from django.contrib.auth.models import User
from users.models import UserProfile

class AdopterService():
    @staticmethod
    def import_from_shelterluv(request_data):
        created_adopters = []
        updated_adopters = []

        for data in request_data["adopters"]:
            profile, created_profile = UserProfile.objects.get_or_create(
                primary_email=data['primary_email'].lower()
            )
            profile.update_from_shelterluv_import(data)

            try:
                user_model = User.objects.get(email__exact=profile.primary_email)
            except User.DoesNotExist:
                user_model = User.objects.create_user(
                    username=profile.primary_email.lower(),
                    email=profile.primary_email.lower(),
                    password='abcdefghij',
                )

            adopter, created_adopter = Adopter.objects.get_or_create(
                user_profile=profile,
                user=user_model,
                defaults={
                    'status': AdopterStatuses.APPROVED,
                    'approved_until': datetime.datetime.today(),
                }
            )
            adopter.update_from_shelterluv_import(data)
            
            if created_adopter:
                created_adopters.append(adopter)
            else:
                updated_adopters.append(adopter)

        response = json.dumps({
            'created': AdopterSerializer(created_adopters, many=True).data,
            'updated': AdopterSerializer(updated_adopters, many=True).data,
        })

        return response


    @staticmethod
    def get_active_booking(self, adopter_id):
        adopter = Adopter.objects.get(pk=adopter_id)
        return Booking.objects.get(adopter=adopter, status=BookingStatus.ACTIVE)