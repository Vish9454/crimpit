# Generated by Django 3.1.7 on 2021-05-31 11:32

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('gyms', '0009_auto_20210531_1125'),
        ('accounts', '0017_questionanswer'),
    ]

    operations = [
        migrations.AddField(
            model_name='userroutefeedback',
            name='gym',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='gym_route_feedback', to='gyms.gymdetails'),
        ),
    ]
