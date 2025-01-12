# Generated by Django 4.2.1 on 2024-07-14 15:07

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('bookings', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Appointment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('type', models.IntegerField(choices=[(0, 'Adults'), (1, 'Puppies'), (2, 'All Ages')])),
                ('instant', models.DateTimeField()),
                ('locked', models.BooleanField(default=False)),
                ('check_in_time', models.DateTimeField(blank=True, null=True)),
                ('check_out_time', models.DateTimeField(blank=True, null=True)),
                ('clothing_description', models.CharField(blank=True, default='', max_length=1000, null=True)),
                ('counselor', models.CharField(blank=True, default='', max_length=1000, null=True)),
                ('booking', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to='bookings.booking')),
            ],
        ),
    ]
