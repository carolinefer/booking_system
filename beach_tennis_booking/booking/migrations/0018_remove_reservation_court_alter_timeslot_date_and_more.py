# Generated by Django 4.2.7 on 2023-11-20 14:27

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('booking', '0017_remove_timeslot_court_remove_timeslot_end_time_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='reservation',
            name='court',
        ),
        migrations.AlterField(
            model_name='timeslot',
            name='date',
            field=models.DateField(),
        ),
        migrations.AlterField(
            model_name='timeslot',
            name='template',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='booking.timeslottemplate'),
        ),
    ]
