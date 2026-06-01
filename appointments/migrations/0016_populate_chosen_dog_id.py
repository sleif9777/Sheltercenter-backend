import datetime

from django.db import migrations


def populate_chosen_dog_id(apps, schema_editor):
    Appointment = apps.get_model("appointments", "Appointment")
    PendingAdoption = apps.get_model("pending_adoptions", "PendingAdoption")
    Dog = apps.get_model("dogs", "Dog")

    ADOPTION = 0
    FTA = 1
    CHOSEN = 2

    appts = Appointment.objects.filter(
        outcome__isnull=False,
        chosen_dog__isnull=False,
        chosen_dog_id__isnull=True,
    ).exclude(chosen_dog="")

    for appt in appts:
        if appt.outcome == CHOSEN:
            try:
                pending = PendingAdoption.objects.get(source_appointment=appt)
                appt.chosen_dog_id = pending.dogID
                appt.save(update_fields=["chosen_dog_id"])
            except PendingAdoption.DoesNotExist:
                pass
        elif appt.outcome in [ADOPTION, FTA]:
            if appt.check_out_time is None:
                continue

            check_out_date = appt.check_out_time.date()
            window_start = check_out_date - datetime.timedelta(days=7)
            window_end = check_out_date + datetime.timedelta(days=7)

            try:
                dog = Dog.objects.get(
                    name=appt.chosen_dog,
                    last_updated__gte=window_start,
                    last_updated__lte=window_end,
                )
                appt.chosen_dog_id = dog.pk
                appt.save(update_fields=["chosen_dog_id"])
            except (Dog.DoesNotExist, Dog.MultipleObjectsReturned):
                pass


def reverse_populate_chosen_dog_id(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("appointments", "0015_add_chosen_dog_id"),
        ("pending_adoptions", "0009_alter_pendingadoption_status"),
        ("dogs", "0011_dog_other_photos"),
    ]

    operations = [
        migrations.RunPython(
            populate_chosen_dog_id,
            reverse_populate_chosen_dog_id,
        ),
    ]
