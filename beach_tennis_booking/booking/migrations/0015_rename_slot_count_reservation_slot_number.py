# Generated by Django 4.2.7 on 2023-11-19 07:06

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('booking', '0014_remove_reservation_block_number_and_more'),
    ]

    operations = [
        migrations.RenameField(
            model_name='reservation',
            old_name='slot_count',
            new_name='slot_number',
        ),
    ]
