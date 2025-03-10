# Generated by Django 4.2.1 on 2024-07-14 15:07

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('admin_appointments', '0001_initial'),
        ('adopters', '0001_initial'),
        ('appointments', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='PendingAdoption',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_instant', models.DateTimeField()),
                ('circumstance', models.IntegerField(choices=[(0, 'Host Weekend'), (1, 'Foster'), (2, 'Appointment'), (3, 'Friend of Foster'), (4, 'Friend of Molly')])),
                ('dog', models.CharField(default='', max_length=50)),
                ('ready_to_roll_instant', models.DateTimeField(blank=True, null=True)),
                ('adopter', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='adopters.adopter')),
                ('paperwork_appointment', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='pending_adoption_paperwork', to='admin_appointments.adminappointment')),
                ('source_appointment', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='pending_adoption', to='appointments.appointment')),
                ('source_appointment_admin', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='pending_adoption_source', to='admin_appointments.adminappointment')),
            ],
        ),
    ]
