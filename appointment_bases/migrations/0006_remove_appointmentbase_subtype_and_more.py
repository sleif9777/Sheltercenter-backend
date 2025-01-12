# Generated by Django 5.1.4 on 2024-12-25 17:28

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('appointment_bases', '0005_alter_appointmentbase_type'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='appointmentbase',
            name='subtype',
        ),
        migrations.AlterField(
            model_name='appointmentbase',
            name='type',
            field=models.IntegerField(choices=[(0, 'Adults'), (1, 'Puppies'), (2, 'All Ages'), (3, 'Paperwork'), (4, 'Surrender'), (5, 'Visit'), (6, 'Donation Drop-Off')]),
        ),
    ]
