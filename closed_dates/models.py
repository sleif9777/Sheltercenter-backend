from django.db import models

# Create your models here.
class ClosedDate(models.Model):
    date = models.DateField(null=False, blank=False)

    #date
    def __repr__(self):
        return ""