from rest_framework import serializers

from .models import Adopter


# REQUESTS


class AdopterDirectoryListingRequestSerializer(serializers.Serializer):
    filterText = serializers.CharField(required=True, allow_blank=False)
    includeArchived = serializers.BooleanField()


class AdopterIDRequestSerializer(serializers.Serializer):
    adopterID = serializers.CharField()

    def validate_adopterID(self, value: str) -> int:
        if not Adopter.objects.filter(pk=int(value)).exists():
            raise serializers.ValidationError("Adopter does not exist.")
        return value


class SendMessageRequestSerializer(AdopterIDRequestSerializer):
    subject = serializers.CharField(allow_blank=True)
    message = serializers.CharField()

    def validate_adopterID(self, value: str) -> int:
        return super().validate_adopterID(value)


class RecentlyUploadedAdoptersRequestSerializer(serializers.Serializer):
    lookbackDays = serializers.ChoiceField(choices=[1, 2, 3, 5, 10], required=False, default=3)


# RESPONSES

class AdopterContactInfoSerializer(serializers.ModelSerializer):
    ID = serializers.IntegerField(source="id")
    firstName = serializers.CharField(source="user_profile.first_name")
    lastName = serializers.CharField(source="user_profile.last_name")
    primaryEmail = serializers.EmailField(source="user_profile.primary_email")
    streetAddress = serializers.CharField(source="user_profile.street_address")
    city = serializers.CharField(source="user_profile.city")
    state = serializers.CharField(source="user_profile.state")
    postalCode = serializers.CharField(source="user_profile.postal_code")
    shelterluvAppID = serializers.CharField(source="shelterluv_app_id")

    class Meta:
        model = Adopter
        fields = [
            "ID",
            "firstName",
            "lastName",
            "primaryEmail",
            "streetAddress",
            "city",
            "state",
            "postalCode",
            "shelterluvAppID",
        ]

class AdopterDemographicsSerializer(AdopterContactInfoSerializer):
    internalNotes = serializers.CharField(source="internal_notes")
    phoneNumber = serializers.CharField(source="user_profile.phone_number")
    approvedUntilISO = serializers.CharField(source="approved_until_iso")
    approvalExpired = serializers.BooleanField(source="approval_expired")
    restrictedCalendar = serializers.BooleanField(source="user_profile.adoption_completed")
    status = serializers.IntegerField()
    bookingHistory = serializers.JSONField(source="booking_history")

    class Meta:
        model = Adopter
        fields = [
            "ID",
            "firstName",
            "lastName",
            "internalNotes",
            "primaryEmail",
            "phoneNumber",
            "approvedUntilISO",
            "approvalExpired",
            "restrictedCalendar",
            "status",
            "bookingHistory",
            "streetAddress",
            "city",
            "state",
            "postalCode",
            "shelterluvAppID",
        ]


class AdopterPreferencesRequestSerializer(AdopterIDRequestSerializer):
    activityLevel = serializers.IntegerField(required=False, allow_null=True)
    agePreference = serializers.IntegerField(required=False, allow_null=True)
    genderPreference = serializers.IntegerField(required=False, allow_null=True)

    bringingDog = serializers.BooleanField(required=False)
    hasDogs = serializers.BooleanField(required=False)
    hasCats = serializers.BooleanField(required=False)
    hasOtherPets = serializers.BooleanField(required=False)

    otherPetsComment = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
    )

    housingType = serializers.IntegerField(required=False, allow_null=True)
    housingOwnership = serializers.IntegerField(required=False, allow_null=True)

    hasFence = serializers.BooleanField(required=False)
    lowShed = serializers.BooleanField(required=False)
    lowAllergy = serializers.BooleanField(required=False)
    mobility = serializers.BooleanField(required=False)

    minWeightPreference = serializers.IntegerField(required=False, allow_null=True)
    maxWeightPreference = serializers.IntegerField(required=False, allow_null=True)

    adopterNotes = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
    )

    internalNotes = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
    )


class AdopterPreferencesResponseSerializer(serializers.ModelSerializer):
    adopterID = serializers.IntegerField(source="id")
    activityLevel = serializers.IntegerField(
        source="activity_level", required=False, allow_null=True
    )
    agePreference = serializers.IntegerField(
        source="age_preference", required=False, allow_null=True
    )
    agePreferenceDisplay = serializers.CharField(
        source="age_preference_display", required=False, allow_null=True
    )
    applicationComments = serializers.CharField(
        source="application_comments", required=False, allow_null=True
    )
    genderPreference = serializers.IntegerField(
        source="gender_preference", required=False, allow_null=True
    )
    genderPreferenceDisplay = serializers.CharField(
        source="gender_preference_display", required=False, allow_null=True
    )
    bringingDog = serializers.BooleanField(source="bringing_dog", required=False)
    hasDogs = serializers.BooleanField(source="dogs_in_home", required=False)
    hasCats = serializers.BooleanField(source="cats_in_home", required=False)
    hasOtherPets = serializers.BooleanField(source="other_pets_in_home", required=False)
    otherPetsComment = serializers.CharField(
        source="other_pets_comment",
        required=False,
        allow_blank=True,
        allow_null=True,
    )
    housingType = serializers.IntegerField(source="housing_type", required=False, allow_null=True)
    housingOwnership = serializers.IntegerField(source="homeowner", required=False, allow_null=True)
    hasFence = serializers.BooleanField(source="has_fence", required=False)
    lowShed = serializers.BooleanField(source="low_allergy", required=False)
    mobility = serializers.BooleanField(required=False)
    minWeightPreference = serializers.IntegerField(
        source="min_weight_preference", required=False, allow_null=True
    )
    maxWeightPreference = serializers.IntegerField(
        source="max_weight_preference", required=False, allow_null=True
    )
    adopterNotes = serializers.CharField(
        source="adopter_notes", required=False, allow_blank=True, allow_null=True
    )
    internalNotes = serializers.CharField(
        source="internal_notes", required=False, allow_blank=True, allow_null=True
    )

    class Meta:
        model = Adopter
        fields = [
            "adopterID",
            "activityLevel",
            "agePreference",
            "agePreferenceDisplay",
            "genderPreference",
            "genderPreferenceDisplay",
            "applicationComments",
            "bringingDog",
            "hasDogs",
            "hasCats",
            "hasOtherPets",
            "otherPetsComment",
            "housingType",
            "housingOwnership",
            "hasFence",
            "lowShed",
            "mobility",
            "minWeightPreference",
            "maxWeightPreference",
            "adopterNotes",
            "internalNotes",
        ]


class AdopterValueLabelPairSerializer(serializers.HyperlinkedModelSerializer):
    ID = serializers.IntegerField(source="id")
    disambiguatedName = serializers.CharField(source="user_profile.disambiguated_name")

    class Meta:
        model = Adopter
        fields = [
            "ID",
            "disambiguatedName",
        ]


class DirectoryAdopterSerializer(serializers.HyperlinkedModelSerializer):
    ID = serializers.IntegerField(source="id")
    fullName = serializers.CharField(source="user_profile.full_name")
    primaryEmail = serializers.EmailField(source="user_profile.primary_email")
    status = serializers.IntegerField()

    class Meta:
        model = Adopter
        fields = ["ID", "fullName", "primaryEmail", "status"]


class RecentlyUploadedAdoptersResponseSerializer(serializers.HyperlinkedModelSerializer):
    ID = serializers.IntegerField(source="id")
    primaryEmail = serializers.EmailField(source="user_profile.primary_email")
    disambiguatedName = serializers.CharField(source="user_profile.disambiguated_name")
    statusDisplay = serializers.CharField(source="status_display")
    lastUploaded = serializers.DateTimeField(source="last_uploaded_display")

    class Meta:
        model = Adopter
        fields = ["ID", "primaryEmail", "disambiguatedName", "statusDisplay", "lastUploaded"]
