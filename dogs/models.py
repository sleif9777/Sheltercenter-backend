from adopters.models import Adopter
from django.db import models

from .enums import *

# Create your models here.
class Dog(models.Model):
    name = models.CharField(default="", max_length=100, null=False, blank=False)
    shelterluv_id = models.IntegerField(null=False, blank=False)
    description = models.CharField(default="", max_length=5000, null=False, blank=True)
    photo_url = models.CharField(default="", max_length=200, null=False, blank=True)
    age_months = models.IntegerField(null=True,blank=True)
    weight = models.IntegerField(null=True,blank=True)
    sex = models.IntegerField(choices=DogSex.choices, null=False, blank=False)
    breed = models.CharField(default="", max_length=100, null=True, blank=True)
    fun_size = models.BooleanField(default=False)
    publishable = models.BooleanField(default=False)
    available_date = models.DateField(null=True, blank=True)
    unavailable_date = models.DateField(null=True, blank=True)
    status = models.IntegerField(choices=DogStatus.choices, null=False, blank=False)
    interest_adopters = models.ManyToManyField(Adopter, blank=True)

    @property
    def available_date_iso(self):
        return self.available_date.isoformat()

    @property
    def unavailable_date_iso(self):
        return self.unavailable_date.isoformat()

    @property
    def interest_count(self):
        return self.interest_adopters.count()

    @property
    def available_now(self):
        return self.status == DogStatus.AVAILABLE_NOW

    def __repr__(self):
        self.name

    def __str__(self):
        return f"{self.name} [{self.id}, SL-{self.shelterluv_id}]"
