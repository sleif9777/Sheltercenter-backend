from django.db import models


# Create your models here.
class EmailTemplate(models.Model):
    #type
    #content
    #active
    #file1
    #file2
    #allowed editors

    def send(self):
        return ""

    class Meta:
        verbose_name = "email template"