# Generated by Django 3.1.7 on 2021-08-09 07:00

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0024_auto_20210716_1144'),
    ]

    operations = [
        migrations.AddField(
            model_name='userroutefeedback',
            name='first_time_read',
            field=models.BooleanField(default=False, verbose_name='First Time Read'),
        ),
        migrations.AddField(
            model_name='userroutefeedback',
            name='second_time_read',
            field=models.BooleanField(default=False, verbose_name='Second Time Read'),
        ),
    ]
