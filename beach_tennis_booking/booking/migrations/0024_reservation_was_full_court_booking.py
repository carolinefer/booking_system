# Generated by Django 4.2.7 on 2023-11-20 21:57

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('booking', '0023_reservationtimeslotmaster_is_active'),
    ]

    operations = [
        migrations.AddField(
            model_name='reservation',
            name='was_full_court_booking',
            field=models.BooleanField(default=False),
        ),
    ]
