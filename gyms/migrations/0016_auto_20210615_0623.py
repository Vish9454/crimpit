# Generated by Django 3.1.7 on 2021-06-15 06:23

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('gyms', '0015_auto_20210611_0848'),
    ]

    operations = [
        migrations.AlterField(
            model_name='announcement',
            name='template',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='template_announcement', to='gyms.preloadedtemplate'),
        ),
    ]
