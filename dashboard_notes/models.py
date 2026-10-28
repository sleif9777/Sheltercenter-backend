from django.db import models
from django.utils import timezone

from dogs.models import Dog


class DashboardNote(models.Model):
    """A short-lived note (e.g. "Offsite") shown on the dashboard's Notes tab.

    Linked to a Dog when the dog is in the system, otherwise identified by `dog_name` alone. A dog
    can have several notes at once, and deleting a note never touches the Dog. A note with
    `show_until` set is deleted automatically after that day.
    """

    created_instant = models.DateTimeField(auto_now_add=True)
    dog = models.ForeignKey(
        Dog, null=True, blank=True, on_delete=models.CASCADE, related_name="dashboard_notes"
    )
    # Only used when `dog` is empty
    dog_name = models.CharField(default="", max_length=100, blank=True)
    note = models.CharField(max_length=200)
    # Last day the note shows; empty to keep it until someone removes it
    show_until = models.DateField(null=True, blank=True)

    @classmethod
    def delete_expired(cls) -> None:
        cls.objects.filter(show_until__lt=timezone.localdate()).delete()

    @property
    def display_name(self) -> str:
        return self.dog.name if self.dog else self.dog_name

    def __str__(self) -> str:
        return f"{self.display_name}: {self.note}"

    class Meta:
        verbose_name = "dashboard note"
        ordering = ["created_instant"]
