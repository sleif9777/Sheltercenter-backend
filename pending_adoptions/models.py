from adopters.models import Adopter
from bookings.models import Booking
from appointments.models import Appointment
from django.db import models


from .enums import CircumstanceOptions, PendingAdoptionStatus


class PendingAdoption(models.Model):
    # CREATION ITEMS
    created_instant = models.DateTimeField(auto_now_add=True)

    @property
    def created_iso(self):
        return self.created_instant.isoformat()

    circumstance = models.IntegerField(choices=CircumstanceOptions.choices)

    # RELEVANT PARTY ITEMS
    dog = models.CharField(default="", max_length=50)
    dogID = models.IntegerField(null=True, blank=True)
    adopter = models.ForeignKey(Adopter, on_delete=models.CASCADE)

    # EVENT ITEMS
    source_appointment = models.OneToOneField(
        Appointment, null=True, blank=True, on_delete=models.PROTECT, related_name="source_adoption"
    )
    paperwork_appointment = models.OneToOneField(
        Appointment,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="paperwork_adoption",
    )

    @property
    def source_appt_instant(self):
        return self.source_appointment.instant.isoformat()

    @property
    def paperwork_appt_instant(self):
        return self.paperwork_appointment.instant.isoformat()

    # DESCRIPTORS
    @property
    def description(self):
        return f"{self.dog} ({self.adopter.user_profile.full_name})"

    # ADMINISTRATIVE ITEMS
    status = models.IntegerField(choices=PendingAdoptionStatus.choices)

    @property
    def status_display(self):
        return PendingAdoptionStatus(self.status).label

    ready_to_roll_instant = models.DateTimeField(null=True, blank=True)
    heartworm_positive = models.BooleanField(default=False)

    @property
    def hw_display(self):
        if self.status != PendingAdoptionStatus.READY_TO_ROLL:
            return ""

        return "Positive" if self.heartworm_positive else "Negative"

    # ADMINISTRATIVE METHODS
    def mark_status(self, new_status: PendingAdoptionStatus):
        self.status = new_status
        self.save()

    def mark_hw(self, new_hw):
        self.heartworm_positive = new_hw
        self.save()

    @staticmethod
    def adopter_has_open_adoption(adopter: Adopter, exclude_id: int | None = None) -> bool:
        """True if the adopter has an adoption that is neither canceled nor completed."""
        adoptions = PendingAdoption.objects.filter(adopter=adopter).exclude(
            status__in=[PendingAdoptionStatus.CANCELED, PendingAdoptionStatus.COMPLETED]
        )

        if exclude_id is not None:
            adoptions = adoptions.exclude(pk=exclude_id)

        return adoptions.exists()

    def __str__(self):
        return "{0} - {1}".format(self.dog, self.status_display)

    class Meta:
        verbose_name = "pending adoption"
