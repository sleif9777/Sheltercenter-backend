from django.db import models
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

    def __repr__(self):
        ts = self.instant.strftime("%-m/%-d/%y %-I:%M %p")
        return f"Update at {ts} [{self.id}; ADOPTION {self.adoption_id}]"

    def __str__(self):
        return self.__repr__()

    class Meta:
        verbose_name = "pending adoption update"
