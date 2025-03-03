# Generated by Django 3.1.7 on 2021-05-14 16:08

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('gyms', '0003_auto_20210512_0619'),
        ('accounts', '0004_listcategory_routesavelist_userroutefeedback'),
    ]

    operations = [
        migrations.AddField(
            model_name='listcategory',
            name='gym',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='gym_list_category', to='gyms.gymdetails'),
        ),
        migrations.AddField(
            model_name='routesavelist',
            name='gym',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='gym_route_list', to='gyms.gymdetails'),
        ),
    ]
