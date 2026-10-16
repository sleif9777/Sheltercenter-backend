from django.db import models
from django.utils import timezone
from pending_adoptions.models import PendingAdoption


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

    @property
    def instant_iso(self):
        return self.instant.isoformat()

    def __str__(self):
        ts = timezone.localtime(self.instant).strftime("%-m/%-d/%y %-I:%M %p")
        return f"Update at {ts}"

    class Meta:
        verbose_name = "pending adoption update"
