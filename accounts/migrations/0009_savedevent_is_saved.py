# Generated by Django 3.1.7 on 2021-05-19 13:53

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0008_savedevent'),
    ]

    operations = [
        migrations.AddField(
            model_name='savedevent',
            name='is_saved',
            field=models.BooleanField(default=False, verbose_name='Is Saved'),
        ),
    ]
