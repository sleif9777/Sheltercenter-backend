# Generated by Django 5.1.4 on 2024-12-22 04:47

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('adopters', '0003_adopter_internal_notes'),
    ]

    operations = [
        migrations.AddField(
            model_name='adopter',
            name='adopter_notes',
            field=models.CharField(blank=True, default='', max_length=500, null=True),
        ),
    ]
