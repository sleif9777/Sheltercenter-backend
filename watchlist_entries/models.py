from django.db import models

from adopters.models import Adopter
from dogs.models import Dog

# Create your models here.
class WatchlistEntry(models.Model):
    adopter = models.ForeignKey(Adopter, null=False, blank=False, on_delete=models.CASCADE)
    dog = models.ForeignKey(Dog, null=False, blank=False, on_delete=models.CASCADE)