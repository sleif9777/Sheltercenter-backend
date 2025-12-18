from django.db import models

from .enums import EnvironmentType

# Create your models here.
class EnvironmentSettings(models.Model):
    environment_type = models.IntegerField(choices=EnvironmentType.choices)

    # EMAIL SETTINGS
    default_sending_email = models.EmailField(null=False, blank=False)
    test_recipient_email = models.EmailField(null=False, blank=False)
    email_host = models.CharField(max_length=1000, null=False, blank=False)

    # FOSTER-TO-ADOPT FILES
    fta_doc_1_path = models.CharField(max_length=1000, null=True, blank=True)
    fta_doc_2_path = models.CharField(max_length=1000, null=True, blank=True)