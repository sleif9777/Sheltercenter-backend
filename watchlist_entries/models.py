from adopters.models import Adopter
from django.db import models
from dogs.models import Dog


# Create your models here.
class WatchlistEntry(models.Model):
    adopter = models.ForeignKey(Adopter, null=False, blank=False, on_delete=models.CASCADE)
    dog = models.ForeignKey(Dog, null=False, blank=False, on_delete=models.CASCADE)

    def __repr__(self):
        return f"{self.adopter.__repr__()} | {self.dog.__repr__()} [{self.id}; ADPT {self.adopter_id}; DOG {self.dog_id}]"

    def __str__(self):
        return self.__repr__()

    class Meta:
        verbose_name = "watchlist entry"
        verbose_name_plural = "watchlist entries"