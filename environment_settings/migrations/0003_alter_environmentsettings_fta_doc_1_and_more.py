# Generated by Django 5.1.4 on 2025-01-12 16:33

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('environment_settings', '0002_environmentsettings_default_sending_email_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='environmentsettings',
            name='fta_doc_1',
            field=models.FileField(blank=True, null=True, upload_to='media/'),
        ),
        migrations.AlterField(
            model_name='environmentsettings',
            name='fta_doc_2',
            field=models.FileField(blank=True, null=True, upload_to='media/'),
        ),
    ]
