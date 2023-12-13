# Generated by Django 4.2.7 on 2023-11-28 12:02

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('booking', '0026_timeslot_booking_type'),
    ]

    operations = [
        migrations.AddField(
            model_name='timeslottemplate',
            name='booking_type',
            field=models.CharField(choices=[('individual', 'Individual'), ('full_court', 'Full Court')], default='individual', max_length=15),
        ),
    ]
