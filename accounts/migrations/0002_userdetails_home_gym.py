# Generated by Django 3.1.7 on 2021-05-10 12:13

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('gyms', '0002_gymlayout_layoutsection_sectionwall_wallroute'),
        ('accounts', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='userdetails',
            name='home_gym',
            field=models.ManyToManyField(related_name='user_home_gym', to='gyms.GymDetails'),
        ),
    ]
