import json

from rest_framework import serializers
from .models import Adopter

class AdopterBaseSerializer(serializers.HyperlinkedModelSerializer):
    ID = serializers.IntegerField(source="id")
    
    primaryEmail = serializers.EmailField(source="user_profile.primary_email")
    firstName = serializers.CharField(source="user_profile.first_name")
    lastName = serializers.CharField(source="user_profile.last_name")
    
    fullName = serializers.CharField(source="user_profile.full_name")
    disambiguatedName = serializers.CharField(source="user_profile.disambiguated_name")
    
    status = serializers.IntegerField()
    lastUploaded = serializers.DateTimeField(source="last_uploaded")

    class Meta:
        model = Adopter
        fields = [
            'ID', 
            
            'primaryEmail', 
            'firstName',
            'lastName',
            
            'fullName',
            'disambiguatedName',
            
            'status',
            'lastUploaded'
        ]


class AdopterSerializer(serializers.HyperlinkedModelSerializer):
    ID = serializers.IntegerField(source="id")
    
    primaryEmail = serializers.EmailField(source="user_profile.primary_email")
    firstName = serializers.CharField(source="user_profile.first_name")
    lastName = serializers.CharField(source="user_profile.last_name")
    fullName = serializers.CharField(source="user_profile.full_name")
    disambiguatedName = serializers.CharField(source="user_profile.disambiguated_name")
    city = serializers.CharField(source="user_profile.city")
    state = serializers.CharField(source="user_profile.state")
    phoneNumber = serializers.CharField(source="user_profile.phone_number")
    status = serializers.IntegerField()
    userID = serializers.IntegerField(source="user_profile.id")
    
    shelterluvAppID = serializers.CharField(source="shelterluv_app_id")
    shelterluvID = serializers.CharField(source="shelterluv_id")
    approvedUntil = serializers.DateField(source="approved_until")
    lastUploaded = serializers.DateTimeField(source="last_uploaded")
    
    applicationComments = serializers.CharField(source="application_comments")
    internalNotes = serializers.CharField(source="internal_notes")
    adopterNotes = serializers.CharField(source="adopter_notes")

    housingOwnership = serializers.IntegerField(source="homeowner")
    housingType = serializers.IntegerField(source="housing_type")
    activityLevel = serializers.IntegerField(source="activity_level")
    hasFence = serializers.BooleanField(source="has_fence")
    dogsInHome = serializers.BooleanField(source="dogs_in_home")
    catsInHome = serializers.BooleanField(source="cats_in_home")
    otherPetsInHome = serializers.BooleanField(source="other_pets_in_home")
    otherPetsComment = serializers.CharField(source="other_pets_comment")

    genderPreference = serializers.IntegerField(source="gender_preference")
    agePreference = serializers.IntegerField(source="age_preference")
    minWeightPreference = serializers.IntegerField(source="min_weight_preference")
    maxWeightPreference = serializers.IntegerField(source="max_weight_preference")
    lowAllergy = serializers.BooleanField(source="low_allergy")
    
    mobility = serializers.BooleanField()
    bringingDog = serializers.BooleanField(source="bringing_dog")

    restrictedCalendar = serializers.BooleanField(source="user_profile.adoption_completed")

    class Meta:
        model = Adopter
        fields = [
            'ID', 
            
            'primaryEmail', 
            'firstName',
            'lastName',
            'fullName',
            'disambiguatedName',
            'city',
            'state',
            'phoneNumber',
            'status',  
            'userID',

            'shelterluvAppID',   
            'shelterluvID',   
            'approvedUntil', 
            'lastUploaded',

            'applicationComments',
            'internalNotes',
            'adopterNotes',

            'housingOwnership',
            'housingType',
            'activityLevel',
            'hasFence',
            'dogsInHome',
            'catsInHome',
            'otherPetsInHome',
            'otherPetsComment',

            'genderPreference',
            'agePreference',
            'minWeightPreference',
            'maxWeightPreference',
            'lowAllergy',

            'mobility',
            'bringingDog',

            'restrictedCalendar'
        ]