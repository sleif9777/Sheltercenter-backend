from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("bookings", "0009_alter_booking_status"),
    ]

    operations = [
        migrations.AddField(
            model_name="booking",
            name="cancel_token",
            field=models.UUIDField(blank=True, null=True, unique=True),
        ),
        migrations.AddField(
            model_name="booking",
            name="cancel_token_expires_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
