from django.db import models

from pending_adoptions.models import PendingAdoption

from .enums import PendingAdoptionUpdateType

# Create your models here.
class PendingAdoptionUpdate(models.Model):
    instant = models.DateTimeField(auto_now_add=True)
    adoption = models.ForeignKey(
        PendingAdoption,
        null=False,
        blank=False,
        on_delete=models.PROTECT,
        related_name="updates"
    )
