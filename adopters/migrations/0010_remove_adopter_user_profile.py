# Generated by Django 5.1.4 on 2024-12-28 22:03

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('adopters', '0009_adopter_last_uploaded'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='adopter',
            name='user_profile',
        ),
    ]
