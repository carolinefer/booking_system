# Generated by Django 4.2.7 on 2023-11-27 12:29

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('booking', '0024_reservation_was_full_court_booking'),
    ]

    operations = [
        migrations.AddField(
            model_name='reservationtimeslotmaster',
            name='is_full_court',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='timeslot',
            name='is_full_court_booked',
            field=models.BooleanField(default=False),
        ),
    ]