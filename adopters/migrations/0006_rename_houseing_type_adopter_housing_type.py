# Generated by Django 5.1.4 on 2024-12-22 05:16

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('adopters', '0005_adopter_bringing_dog_adopter_cats_in_home_and_more'),
    ]

    operations = [
        migrations.RenameField(
            model_name='adopter',
            old_name='houseing_type',
            new_name='housing_type',
        ),
    ]
