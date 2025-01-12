# Generated by Django 5.1.4 on 2024-12-24 19:23

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('appointment_bases', '0004_alter_appointmentbase_type'),
    ]

    operations = [
        migrations.AlterField(
            model_name='appointmentbase',
            name='type',
            field=models.IntegerField(choices=[(0, 'Adults'), (1, 'Puppies'), (2, 'All Ages'), (3, 'Surrender'), (4, 'Paperwork'), (5, 'Visit'), (6, 'Donation Drop-Off')]),
        ),
    ]
