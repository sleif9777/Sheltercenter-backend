# Generated by Django 5.1.4 on 2024-12-21 18:51

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('appointment_bases', '0003_appointmentbase_subtype'),
    ]

    operations = [
        migrations.AlterField(
            model_name='appointmentbase',
            name='type',
            field=models.IntegerField(choices=[(0, 'Adults'), (1, 'Puppies'), (2, 'All Ages'), (3, 'Host Weekend/Chosen'), (4, 'Surrender'), (5, 'Paperwork'), (6, 'Visit'), (7, 'Donation Drop-Off')]),
        ),
    ]
