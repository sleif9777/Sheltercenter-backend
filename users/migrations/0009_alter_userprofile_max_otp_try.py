# Generated by Django 5.1.4 on 2024-12-28 17:50

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0008_remove_userprofile_alert_on_date_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='userprofile',
            name='max_otp_try',
            field=models.IntegerField(default=3),
        ),
    ]
