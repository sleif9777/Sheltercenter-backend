# Generated by Django 4.2.1 on 2024-12-16 19:53

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('adopters', '0001_initial'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='adopter',
            name='user',
        ),
        migrations.AddField(
            model_name='adopter',
            name='primary_email',
            field=models.EmailField(default='', max_length=100, unique=True),
        ),
    ]
