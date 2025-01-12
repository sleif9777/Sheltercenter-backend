# Generated by Django 4.2.1 on 2024-10-24 18:28

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('appointments', '0002_remove_appointment_booking'),
        ('bookings', '0003_booking_status'),
    ]

    operations = [
        migrations.AddField(
            model_name='booking',
            name='booking',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to='appointments.appointment'),
        ),
    ]
