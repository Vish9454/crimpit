# Generated by Django 3.1.7 on 2021-05-20 11:50

import django.contrib.postgres.fields
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0010_auto_20210519_1402'),
    ]

    operations = [
        migrations.AlterField(
            model_name='userpreference',
            name='grading',
            field=django.contrib.postgres.fields.ArrayField(base_field=models.CharField(blank=True, max_length=100, null=True), blank=True, null=True, size=None, verbose_name='Grading'),
        ),
    ]
