# Generated by Django 5.1.4 on 2025-01-02 00:31

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('pending_adoption_updates', '0001_initial'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='pendingadoptionupdate',
            name='type',
        ),
    ]
