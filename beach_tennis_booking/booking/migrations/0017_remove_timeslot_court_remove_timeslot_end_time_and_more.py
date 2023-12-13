# Generated by Django 4.2.7 on 2023-11-20 09:38

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('booking', '0016_reservation_slot_count'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='timeslot',
            name='court',
        ),
        migrations.RemoveField(
            model_name='timeslot',
            name='end_time',
        ),
        migrations.RemoveField(
            model_name='timeslot',
            name='level',
        ),
        migrations.RemoveField(
            model_name='timeslot',
            name='player_type',
        ),
        migrations.RemoveField(
            model_name='timeslot',
            name='start_time',
        ),
        migrations.AddField(
            model_name='timeslot',
            name='date',
            field=models.DateField(null=True),
        ),
        migrations.CreateModel(
            name='TimeSlotTemplate',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('start_time', models.TimeField()),
                ('end_time', models.TimeField()),
                ('court', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='booking.court')),
                ('level', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='booking.gamelevel')),
                ('player_type', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='booking.playertype')),
            ],
        ),
        migrations.AddField(
            model_name='timeslot',
            name='template',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='booking.timeslottemplate'),
        ),
    ]