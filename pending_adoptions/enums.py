from django.db import models
from enum import Enum

class CircumstanceOptions(models.IntegerChoices, Enum):
        HOST_WEEKEND = 0, "Host Weekend"
        FOSTER = 1, "Foster"
        APPOINTMENT = 2, "Appointment"
        OPEN_HOUSE = 6, "Open House"
        FRIEND_OF_FOSTER = 3, "Friend of Foster"
        FRIEND_OF_MOLLY = 4, "Friend of Molly"
        OTHER = 5, "Other"

class PendingAdoptionStatus(models.IntegerChoices, Enum):
        CHOSEN = 0, "Chosen"
        NEEDS_VETTING = 1, "Needs Vetting"
        NEEDS_WELL_CHECK = 2, "Needs Well Check"
        READY_TO_ROLL = 3, "Ready"
        COMPLETED = 4, "Completed"
        CANCELED = 5, "Canceled"