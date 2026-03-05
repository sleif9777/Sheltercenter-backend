from django.db import models


# Create your models here.
class ClosedDate(models.Model):
    date = models.DateField(null=False, blank=False)

    def __repr__(self):
        return f"Closed Date {self.date.strftime('%-m/%-d/%y')} [{self.id}]"

    def exists_for_date(cls, date):
        return cls.objects.filter(date=date).exists()

    exists_for_date = classmethod(exists_for_date)