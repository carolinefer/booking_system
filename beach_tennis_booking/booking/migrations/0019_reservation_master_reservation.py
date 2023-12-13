# Generated by Django 4.2.7 on 2023-11-20 15:21

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('booking', '0018_remove_reservation_court_alter_timeslot_date_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='reservation',
            name='master_reservation',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='linked_reservations', to='booking.reservation'),
        ),
    ]
