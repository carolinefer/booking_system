# Generated by Django 4.2.7 on 2023-11-19 07:15

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('booking', '0015_rename_slot_count_reservation_slot_number'),
    ]

    operations = [
        migrations.AddField(
            model_name='reservation',
            name='slot_count',
            field=models.IntegerField(default=1),
        ),
    ]
