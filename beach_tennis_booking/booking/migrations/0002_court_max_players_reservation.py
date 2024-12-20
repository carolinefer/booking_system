# Generated by Django 4.2.7 on 2023-11-12 11:10

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('booking', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='court',
            name='max_players',
            field=models.IntegerField(default=4),
        ),
        migrations.CreateModel(
            name='Reservation',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('reserved_on', models.DateTimeField(auto_now_add=True)),
                ('slot_count', models.IntegerField(default=1)),
                ('court', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='booking.court')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
